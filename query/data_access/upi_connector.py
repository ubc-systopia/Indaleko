from typing import Any

from arango import ArangoClient


class UPIConnector:
    """
    Connector for the Unified Personal Index (UPI) data store using ArangoDB.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
    ):
        """
        Initialize the UPI connector.

        Args:
            host (str): ArangoDB host
            port (int): ArangoDB port
            username (str): ArangoDB username
            password (str): ArangoDB password
            database (str): Name of the database to use
        """
        self.client = ArangoClient(hosts=f"http://{host}:{port}")
        self.db = self.client.db(database, username=username, password=password)

    def execute_aql(
        self,
        query: str,
        bind_vars: dict[str, Any] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute an AQL query on the UPI data store.

        Args:
            query (str): The AQL query to execute
            bind_vars (Dict[str, Any], optional): Bind variables for the query

        Returns:
            List[Dict[str, Any]]: The query results
        """
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return [doc for doc in cursor]

    def search_by_filename(self, filename: str) -> list[dict[str, Any]]:
        """
        Search for files by filename in the UPI.

        Args:
            filename (str): The filename to search for

        Returns:
            List[Dict[str, Any]]: List of matching file information
        """
        query = """
        FOR file IN files
            FILTER LIKE(file.name, @filename, true)
            RETURN {
                name: file.name,
                path: file.path,
                size: file.size,
                modified: file.modified
            }
        """
        return self.execute_aql(query, bind_vars={"filename": f"%{filename}%"})

    def insert_file(self, file_info: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new file record into the UPI.

        Args:
            file_info (Dict[str, Any]): Information about the file to insert

        Returns:
            Dict[str, Any]: The inserted file record
        """
        collection = self.db.collection("files")
        return collection.insert(file_info)

    def update_file(self, file_id: str, file_info: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing file record in the UPI.

        Args:
            file_id (str): The ID of the file to update
            file_info (Dict[str, Any]): Updated information about the file

        Returns:
            Dict[str, Any]: The updated file record
        """
        collection = self.db.collection("files")
        return collection.update({"_key": file_id}, file_info)

    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file record from the UPI.

        Args:
            file_id (str): The ID of the file to delete

        Returns:
            bool: True if the file was successfully deleted, False otherwise
        """
        collection = self.db.collection("files")
        return collection.delete({"_key": file_id})

    def close(self):
        """
        Close the connection to the UPI data store.
        """
        self.client.close()
