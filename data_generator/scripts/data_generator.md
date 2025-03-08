# Data Inputs for the Data Generator

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

#### `file.name`
- **Pattern**: Character pattern.
- **Command**: One of `"starts"`, `"ends"`, `"contains"`, `"exactly"`.
- **Extension**: One of `[".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]`.

#### `timestamps`
- **Default Bounds**: `starttime = 2019-10-25`, `endtime = datetime.now()`.
- **Format**: `YYYY-MM-DDTHH:MM:SS`.
- **Commands**:
  - `"equal"`: Requires `starttime = endtime`.
  - `"range"`: Requires `starttime < endtime`.

#### `file.size`
- **Default Min/Max**: `1B - 10GB`.
- **Commands**: `"equal"`, `"range"`, `"greater_than"`, `"less_than"`.

#### `file.directory`
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
- **Location**: Specific address or coordinates.
- **Command**: `"at"` (specific location) or `"within"` (radius in km).
- **Timestamp**: One of `"birthtime"`, `"modified"`, `"changed"`, `"accessed"`.

### **Ambient Music**
- Attributes include `track_name`, `artist_name`, `album_name`, `source`, `device_type`, etc.

### **Ecobee Temperature**
- Temperature, humidity, and target temperature each have `start`, `end`, and `command`.
- **HVAC mode**: One of `["heat", "cool", "auto", "off"]`.
- **HVAC state**: One of `["heating", "cooling", "fan", "idle"]`.
- **Timestamp**: One of `"birthtime"`, `"modified"`, `"changed"`, `"accessed"`.