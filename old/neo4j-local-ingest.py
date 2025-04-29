import ctypes
import os
import stat
from datetime import datetime

from neo4j import GraphDatabase, basic_auth

# Windows API setup for getting file reference number
_GetFileInformationByHandleEx = ctypes.windll.kernel32.GetFileInformationByHandleEx
_FILE_ID_INFO = 38


class FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                ("FileId", ctypes.c_ulonglong * 2)]


def get_file_info(path):
    hfile = ctypes.windll.kernel32.CreateFileW(
        path, 0, 0, None, 3, 0x02000000, None)
    if hfile is None:
        return None
    info = FILE_ID_INFO()
    res = _GetFileInformationByHandleEx(
        hfile, _FILE_ID_INFO, ctypes.byref(info), ctypes.sizeof(info))
    ctypes.windll.kernel32.CloseHandle(hfile)
    if res == 0:
        return None
    return info


# Connect to Neo4j with your credentials
driver = GraphDatabase.driver(
    "bolt://192.168.80.128:7687", auth=basic_auth("neo4j", "Password""))

def enumerate_files(path):
    nodes = []
    relationships = []
    BATCH_SIZE = 5000

    for dirpath, dirnames, filenames in os.walk(path):
        # Get properties for directory
        dir_info = get_file_info(dirpath)
        dir_stats = os.stat(dirpath)
        dir_created = datetime.fromtimestamp(
            dir_stats[stat.ST_CTIME]).isoformat()
        dir_modified = datetime.fromtimestamp(
            dir_stats[stat.ST_MTIME]).isoformat()
        dir_accessed = datetime.fromtimestamp(
            dir_stats[stat.ST_ATIME]).isoformat()
        # Add directory node to batch
        nodes.append((dirpath, 'directory', None, dir_created, dir_modified,
                     dir_accessed, dir_info.FileId if dir_info else None))

        for dirname in dirnames:
            # Get properties for sub-directory
            try:
                subdir_path = os.path.join(dirpath, dirname)
                subdir_info = get_file_info(subdir_path)
                subdir_stats = os.stat(subdir_path)
                subdir_created = datetime.fromtimestamp(
                    subdir_stats[stat.ST_CTIME]).isoformat()
                subdir_modified = datetime.fromtimestamp(
                    subdir_stats[stat.ST_MTIME]).isoformat()
                subdir_accessed = datetime.fromtimestamp(
                    subdir_stats[stat.ST_ATIME]).isoformat()
            except:
                continue # skip on error
            # Add sub-directory node to batch
            nodes.append((subdir_path, 'directory', None, subdir_created, subdir_modified,
                         subdir_accessed, subdir_info.FileId if subdir_info else None))
            # Add relationship to batch
            relationships.append((dirpath, subdir_path))

        for filename in filenames:
            # Get properties for file
            file_path = os.path.join(dirpath, filename)
            file_info = get_file_info(file_path)
            file_stats = os.stat(file_path)
            file_created = datetime.fromtimestamp(
                file_stats[stat.ST_CTIME]).isoformat()
            file_modified = datetime.fromtimestamp(
                file_stats[stat.ST_MTIME]).isoformat()
            file_accessed = datetime.fromtimestamp(
                file_stats[stat.ST_ATIME]).isoformat()
            file_length = file_stats[stat.ST_SIZE]
            # Add file node to batch
            nodes.append((file_path, 'file', file_length, file_created, file_modified,
                         file_accessed, file_info.FileId if file_info else None))
            # Add relationship to batch
            relationships.append((dirpath, file_path))

        # If batch size is reached, write to database
        if len(nodes) >= BATCH_SIZE:
            with driver.session() as session:
                session.execute_write(create_nodes, nodes)
                session.execute_write(create_relationships, relationships)
            # Clear batches
            nodes = []
            relationships = []

    # Write any remaining nodes and relationships to database
    if nodes or relationships:
        with driver.session() as session:
            session.execute_write(create_nodes, nodes)
            session.execute_write(create_relationships, relationships)

def create_nodes(tx, nodes):
    for node in nodes:
        tx.run("MERGE (a:FileSystemObject {name: $name, type: $type}) "
               "ON CREATE SET a.name = $name, a.type = $type, a.length = $length, "
               "a.created = $created, a.modified = $modified, a.accessed = $accessed, a.file_id = $file_id",
               name=node[0], type=node[1], length=node[2], created=node[3], modified=node[4], accessed=node[5], file_id=node[6])


def create_relationships(tx, relationships):
    for relationship in relationships:
        tx.run("MATCH (a:FileSystemObject {name: $name1}), (b:FileSystemObject {name: $name2}) "
               "MERGE (a)-[:CONTAINS]->(b) "
               "MERGE (b)-[:CONTAINED_BY]->(a)",
               name1=relationship[0], name2=relationship[1])


# Replace 'C:\\' with the path of the volume you want to enumerate.
enumerate_files('C:\\')
