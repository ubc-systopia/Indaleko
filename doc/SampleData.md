# This is annotation of data entries

## Indexer Example

This was from a file system indexer for a local Windows file system.  Note that
the captured fields are dynamically determined via introspection relative to
what is available from the python `stat` call interface and thus could vary:

```json
{
    "st_atime": 1693971009.3509176,
    "st_atime_ns": 1693971009350917600,
    "st_birthtime": 1664911875.5260036,
    "st_birthtime_ns": 1664911875526003700,
    "st_ctime": 1664911875.5260036,
    "st_ctime_ns": 1664911875526003700,
    "st_dev": 2756347094955649599,
    "st_file_attributes": 32,
    "st_gid": 0,
    "st_ino": 30117822508602748,
    "st_mode": 33206,
    "st_mtime": 1664911767.6757722,
    "st_mtime_ns": 1664911767675772200,
    "st_nlink": 1,
    "st_reparse_tag": 0,
    "st_size": 7726678740,
    "st_uid": 0,
    "Name": "TechCommunicationSuite_10_0_LREFDJ.zip",
    "Path": "d:\\",
    "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\TechCommunicationSuite_10_0_LREFDJ.zip",
    "Indexer": "0793b4d5-e549-4cb6-8177-020a738b66b7",
    "Volume GUID": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c"
}
```

The fields are:

* `st_atime` - this corresponds to the "access time" field of the file and
  represents some approximation of the last time the file was accessed.  It is
  not updated in real-time typically to avoid the high overhead of doing so.
  This timestamp is relative to the epoch (January 1, 1970)
*  `st_atime_ns` - the UNIX derived representation splits it into second and
  nano-second representations, this is the nanosecond representation
*  `st_birthtime` - if present, this is the timestamp of when the file was
  created relative to the epoch (January 1, 1970)
* `st_birthtime_ns` - if present, this is the timestamp in nanoseconds of when
  the file was created
* `st_ctime` - this is the last time the file has changed.  This is relative to
  the epoch (January 1, 1970)
* `st_ctime_ns` - this is the change time in nanoseconds.
* `st_dev` - this is the "device number" which represents an arbitrary but
  system level unique value where the file is stored.
* `st_file_attributes` - this is a numeric representation of the "file
  attributes" such as read-only, hidden, system, etc.
* `st_gid` - this is a numeric representation of the "group identifier". Windows
  does not have any easily mapped equivalent so normally this value is zero on a
  Windows system.
* `st_ino` - this is a numeric representation of the unique "file identifier" of
  the file on the given local volume.  For NTFS on Windows, this represents the
  FID and can be used to open the file.  For UNIX/Linux systems, this represents
  the inode number.
* `st_mode` - this represents the mode (permission) bits of the file.  NTFS on
  Windows has an Access Control List (ACL) scheme, so this is an approximation of that (UNIX/Linux
  systems often support POSIX ACLs as well and construct a similar equivalency mask.)
* `st_mtime` - this represents the last time the _contents_ of the file were
  modified (versus `ctime` which represents when metadata was changed.)  It is
  relative to the UNIX epoch (January 1, 1970)
* `st_mtime_ns`  - this represents the last time the _contents_ of the file were
  modified in nanoseconds since January 1, 1970
* `st_nlink` - this represents the number of links to this file (many file
  systems allow more than one link to a single file, these are often referred to
  as _hard links_.)
* `st_reparse_tag` - this is a Windows specific concept that generalizes on
  symbolic links and can be used to represent structured files.  A value of zero
  indicates this file does not have a reparse tag.  UNIX/Linux based systems
  will not have this field.
* `st_size` - this is the number of bytes of data present in the file
* `st_uid` - this is the "user ID" that owns the file.  Windows uses SIDs and
  there is no direct mapping, so for Windows this field is not generally useful.
* `Name` - this is the "file name" on the given file system
* `Path` - this is a path name that can be used to access the file by name (the
  "directory" that contains it generally.)
* `URI` - this is a uniform resource identifier that can be used to access the
  file. For Windows, rather than using the transient drive letter based names
  (drive letters are an in-memory construct and can change) we construct a name
  that is portable across machines (e.g., if the drive is moved to a different
  Windows system, this URI will be valid, while the Path may not be.)
* `Indexer` - this identifies the program that generated this data, which can be
  used to ascertain the specific details of other fields in the captured data.
* `Volume GUID` - this is a Windows-specific identifier that is uniquely
  assigned to a given storage volume. A GUID is identical to a UUID and
  represents a unique value assigned to the given drive.
* `UUID` - this is an (optional) UUID assigned by the indexer, that should be
  used for this specific instance of the file.

Note that these fields are _not_ uniformly available across platforms.  The
indexer typically is used to _capture_ data but does not normalize it.

## Ingester Example

An "ingester" is an agent that, typically using indexing data, or metadata
stored in the database, extracts additional information, normalizes that data,
and captures it in the format used by the indexing database (ArangoDB).

Here is the sample ingester element that was generated for one instance of the
indexed file described in the previous section (on indexing).

```json
{
    "Record":
        {
            "Data":             "xQLZxQLWeyJzdF9hdGltZSI6IDE2OTQwNTk1NjAuMzk5MDcxNywgInN0X2F0aW1lX25zIjogMTY5NDA1OTU2MDM5OTA3MTcwMCwgInN0X2JpcnRodGltZSI6IDE2NjQ5MTE4OTkuNzMwNTg4NywgInN0X2JpcnRodGltZV9ucyI6IDE2NjQ5MTE4OTk3MzA1ODg3MDAsICJzdF9jdGltZSI6IDE2NjQ5MTE4OTkuNzMwNTg4NywgInN0X2N0aW1lX25zIjogMTY2NDkxMTg5OTczMDU4ODcwMCwgInN0X2RldiI6IDI3NTYzNDcwOTQ5NTU2NDk1OTksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAxNiwgInN0X2dpZCI6IDAsICJzdF9pbm8iOiAyNTMzMjc0NzkwNDUyMTU5OSwgInN0X21vZGUiOiAxNjg5NSwgInN0X210aW1lIjogMTY2NDkxMTk3MS41ODI3ODY4LCAic3RfbXRpbWVfbnMiOiAxNjY0OTExOTcxNTgyNzg2ODAwLCAic3RfbmxpbmsiOiAxLCAic3RfcmVwYXJzZV90YWciOiAwLCAic3Rfc2l6ZSI6IDAsICJzdF91aWQiOiAwLCAiTmFtZSI6ICJUZWNoQ29tbXVuaWNhdGlvblN1aXRlXzEwXzBfTFJFRkRKIiwgIlBhdGgiOiAiZDpcXCIsICJVUkkiOiAiXFxcXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LTExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxUZWNoQ29tbXVuaWNhdGlvblN1aXRlXzEwXzBfTFJFRkRKIiwgIkluZGV4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2NmI3IiwgIlZvbHVtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyJ9",
            "Attributes":
                {
                    "st_atime": 1694059560.3990717,
                    "st_atime_ns": 1694059560399071700,
                    "st_birthtime": 1664911899.7305887,
                    "st_birthtime_ns": 1664911899730588700,
                    "st_ctime": 1664911899.7305887,
                    "st_ctime_ns": 1664911899730588700,
                    "st_dev": 2756347094955649599,
                    "st_file_attributes": 16,
                    "st_gid": 0,
                    "st_ino": 25332747904521599,
                    "st_mode": 16895,
                    "st_mtime": 1664911971.5827868,
                    "st_mtime_ns": 1664911971582786800,
                    "st_nlink": 1,
                    "st_reparse_tag": 0,
                    "st_size": 0,
                    "st_uid": 0,
                    "Name": "TechCommunicationSuite_10_0_LREFDJ.zip",
                    "Path": "d:\\",
                    "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\TechCommunicationSuite_10_0_LREFDJ.zip", "Indexer": "0793b4d5-e549-4cb6-8177-020a738b66b7",
                    "Volume GUID": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c"
                },
            "Source Identifier":
                {
                    "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                    "Version": "1.0"
                },
            "Timestamp": "2024-01-19T19:49:38.238201+00:00"
        },
        "_key": "f3191095-4dc4-443d-b9b8-e031476abd74",
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\TechCommunicationSuite_10_0_LREFDJ.zip",
        "ObjectIdentifier": "f3191095-4dc4-443d-b9b8-e031476abd74",
        "Timestamps":
        [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2022-10-04T19:31:39.730589+00:00",
                "Description": "Created"
            },
            {
                "Label": "434f7ac1-f71a-4cea-a830-e2ea9a47db5a",
                "Value": "2022-10-04T19:32:51.582787+00:00",
                "Description": "Modified"
            },
            {
                "Label": "581b5332-4d37-49c7-892a-854824f5d66f",
                "Value": "2023-09-07T04:06:00.399072+00:00",
                "Description": "Accessed"
            },
            {
                "Label": "3bdc4130-774f-4e99-914e-0bec9ee47aab",
                "Value": "2022-10-04T19:31:39.730589+00:00",
                "Description": "Changed"
            }
        ],
        "Size": 7726678740,
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
        "UnixFileAttributes": "S_IFDIR",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_NORMAL"
    }
```

### Record

There is a common format for all data elements added to the database in the form
of a **Record**.

A record consists of four fields:
* Data - this is a compressed base64 representation of the raw data captured (if
  any.)  This may contain data we have not processed, though we captured it contemporaneously.
* Attributes - this is a key/value representation of some (or all) the
  attributes related to this specific record.
* Source Identifier - this uniquely identifies the agent that generated this
  record and includes versioning information.
* Timestamp - this identifies, in ISO date format, the time when this record was
  generated.

## Object specific information

Each type of data object captured contains object-specific metadata. There is no
fixed format for this, since we are gathering data from a multitude of sources.

In the sample given below we had the following fields:

* _key - this is the unique index for this object. These are UUIDs. This is
  specific to how ArangoDB works (by specifying the _key field this becomes the
  primary key for the "document" in the database.)
* URI - this is the URI that leads to the specific object
* ObjectIdentifier - this is the unique identifier we generated for the file.
  Note that in this example it is identical to the _key, but this will always be
  present, even if we change databases or use different key values.
* Timestamps: for files, these are normalized versions of the timestamps using
  ISO format timestamp strings (which are more general than epoch based numeric
  time values.)
* Size - this is the size of the file in bytes
* Machine - this is a unique UUID that represents the machine on which this data
  was captured
* Volume - this is a unique UUID that represents the volume on which the data
  was stored.
* UnixFileAttributes - this is a semantic interpretation of the unix file
  attribute bits; the strings used correspond with the standard mnemonic names
  used by the underlying `stat` system call.
* WindowsFileAttributes - this is a semantic interpretation of the Windows file
  attribute bits; the strings used correspond with the standard mnemnoic names
  used by the underlying NtQueryAttributesFile system call.

The contents of these fields will very much depend upon the source of the data
or information.  The function of the various elements is to capture this
metadata in whatever format "makes sense" for the original source.  This permits
us to then mine the data, find relationships, iterate over how we extract the
necessary information, and answer our sample queries.


