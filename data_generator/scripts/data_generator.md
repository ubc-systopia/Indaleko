
# Data Generator:

## Terminology of Different File Types Created by the Data Generator:
- **Truth metadata**: Files containing all queried attributes with random values for the rest.
- **Filler metadata**: Randomly generated metadata that do not fulfill any queried attributes.
- **Truth-like filler metadata**: Files containing some but not all queried attributes while the rest are randomly generated.

## How Metadata is Generated
Each file type is distinguished by UUID:
- `c#....` → Truth files.
- `f#....` → Filler files.

The list is passed to `s5_get_precision_and_recall.py` to determine how many truth files are actually found.

#### Truth Metadata
- Number is based on the config file.
- All queried attributes from the NL query must be present in each truth file.

#### Filler Metadata
- Number of truth-like attributes: **0**.
- Number of filler metadata: `total - truth - truth-like`.

#### Truth-like Filler Metadata
- Hybrid of truth and filler metadata that contains **at least one but not all** truth attributes.
- Constraint: `number of queried attributes > 1` for these metadata to appear.
- Truth-like metadata count: Random number from `[0, number of filler files required]`.

---

## Overview

`self.selected_md_attributes` is a dictionary that contains all the queried attributes for the truth metadata. All other types of metadata depend on this dictionary.

The dictionary is divided into three categories:
- **Posix (Record)**
- **Semantic**
- **Activity**

Populating each category is optional; only queried attributes should be included. If no Activity context is queried, only the Posix and Semantic components should be populated. Similarly, within each metadata category, only the specified attributes need to be populated.

For example, if the query is *"Find me the jpg file that I took yesterday"*, only the **file extension (jpg)** in `file.name` and **birthtime (yesterday’s date)** need to be included.

---

## `self.selected_md_attributes` Structure

```json
{
  "Posix": {
    "file.name": { "pattern": "str", "command": "str", "extension": "str" },
    "timestamps": {
      "birthtime": { "starttime": "str", "endtime": "str" },
      "modified": { "starttime": "str", "endtime": "str" },
      "accessed": { "starttime": "str", "endtime": "str" },
      "changed": { "starttime": "str", "endtime": "str" }
    },
    "file.size": { "target_min": "int | list[int]", "target_max": "int | list[int]", "command": "str" },
    "file.directory": { "location": "str", "local_dir_name": "str" }
  },
  "Semantic": {
    "Content_1": [ { "label": "data" } ],
    "Content_2": [ { "label": "data" } ]
  },
  "Activity": {
    "geo_location": { "location": "str", "command": "str", "km": "int", "timestamp": "str" },
    "ecobee_temp": {
      "temp": { "start": "float", "end": "float", "command": "str" },
      "humidity": { "start": "float", "end": "float", "command": "str" },
      "target_temp": { "start": "float", "end": "float", "command": "str" },
      "Hvac_mode": "str",
      "Hvac_state": "str",
      "timestamp": "str"
    },
    "ambient_music": {
      "track_name": "str",
      "artist_name": "str",
      "playback_position_ms": "int",
      "track_duration_ms": "int",
      "is_currently_playing": "bool",
      "album_name": "str",
      "source": "str",
      "device_type": "str",
      "timestamp": "str"
    }
  }
}
```

---

## **Posix Metadata Details**

### **Static Attributes**
- **PosixFileAttributes**: `"S_IFREG"`
- **WindowsFileAttributes**: `"FILE_ATTRIBUTE_ARCHIVE"`

### **Dynamic Attributes**

#### **file.name**
- **Pattern**: Character pattern.
- **Command**: One of `"starts"`, `"ends"`, `"contains"`, `"exactly"`.
- **Extension**: One of `[".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]`.

#### **timestamps**
- **Default Bounds**: `starttime = 2019-10-25`, `endtime = datetime.now()`.
- **Format**: `YYYY-MM-DDTHH:MM:SS`.

#### **file.size**
- **Default Bounds**: `1B - 10GB`.
- **Commands**: `"equal"`, `"range"`, `"greater_than"`, `"less_than"`.

#### **file.directory**
- **Location**: One of `"google_drive"`, `"dropbox"`, `"icloud"`, `"local"`.
- **local_dir_name**: Only applicable for local files.

---

## **Semantic Metadata Details**

Semantic contexts apply only to text-based files: `"pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"`.

### **Standard Attributes**
- **LastModified**: From Posix metadata.
- **Filename**: From Posix metadata.
- **Filetype**: From Posix metadata.
- **Languages**: Default: `"English"`.

### **Label Types**

| Label Category | Examples |
|---------------|----------|
| **LONG_TAGS** | `"Text"`, `"NarrativeText"`, `"Paragraph"` |
| **LIST_TAGS** | `"List"`, `"ListItem"` |
| **IMAGE_TAGS** | `"Image"`, `"Picture"` |
| **SHORT_TAGS** | `"Title"`, `"Headline"`, `"Page-header"` |
| **NUMBER_TAGS** | `"PageNumber"`, `"Value"` |
| **KEY_VALUE_TAGS** | `"Form"`, `"FormKeysValues"` |
| **BUTTON_TAGS** | `"Checked"`, `"Unchecked"` |

---

## **Activity Metadata Details**

### **Geo-location**
- **location**: Specific address or geographical coordinates.
- **command**: `"at"` (specific location) or `"within"` (radius in km).
- **timestamp**: One of `"birthtime"`, `"modified"`, `"changed"`, `"accessed"`.

### **Ambient Music**
- **track_name**: Name of track/music playing
- **artist_name**: Name of artist
- **playback_position_ms**: playback position of the song
- **track_duration_ms**: length of the song
- **is_playing**: whether the song is playing at the time of activity
- **album_name**: name of album track belongs to
- **source**: one of “spotify”, “apple music”, “youtube music”
- **device_type**: (only when source is spotify) type of device; one of “Computer”, “Smartphone”, ”Speaker”, ”TV”, ”Game_Console”, ”Automobile”, ”Unknown”
- **Timestamp**: One of `"birthtime"`, `"modified"`, `"changed"`, `"accessed"`.

### **Ecobee Temperature**
#### **temperature**
- **Default Bounds**: `-50 - 100`.
- **Commands**: `"equal"`, `"range"`.

#### **humidity**
- **Default Bounds**: `0.0 - 100.0`.
- **Commands**: `"equal"`, `"range"`.

#### **target_temperature**
- **Default Bounds**: `-50 - 100`.
- **Commands**: `"equal"`, `"range"`.

#### **HVAC_mode**
- One of `["heat", "cool", "auto", "off"]`.

#### **HVAC_state**
- One of `["heating", "cooling", "fan", "idle"]`.

#### **Timestamp**
- One of `"birthtime"`, `"modified"`, `"changed"`, `"accessed"`.
