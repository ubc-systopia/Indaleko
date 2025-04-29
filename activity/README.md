# Activity Data

The activity data system consists of three core pieces:

* The framework infrastructure, which provides management services, such as creating ArangoDB collections for each type of activity data being collected, discovery of data sources, and infrastructure to support the collection and storage of the data
* The collectors.  These are modules that know how to collect interesting data from "somewhere".  We don't define the format of the data - the collector does.
* The recorders.  In general, there will be one recorder for a collector, though it may be possible for a single recorder to pull from multiple collectors.  The reverse (multiple recorders for a single collector) is not currently considered in this implementation.  The job of the recorder is to normalize what it can from the data, use semantic labels - preferably "well known" ones whenever possible, but it can make up its own semantic labels, and then store that in the activity data specific collection it has been given by the sytstem (that's part of the "infrastructure").

To make this usable in the LLM query driven system, the recorders must be able to return a description of what each label represents.  It _can_ pull information from the underlying collector, but this isn't required.  For common labels, the same description will be returned for each occurrence of the given label.

For example, we have multiple sources for location information.  We define three "well known" labels: longitude, latitude, and accuracy.  All the location services return additional metadata, but we haven't identified common data types.
