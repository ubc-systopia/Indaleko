"""Activity data models for ablation testing."""

from .ablation_results import (
    AblationQueryTruth,
    AblationResult,
    AblationTestMetadata,
    MetricType,
)
from .activity import ActivityData, ActivityType, TruthData
from .collaboration_activity import CollaborationActivity, Participant
from .location_activity import LocationActivity, LocationCoordinates
from .media_activity import MediaActivity, MediaType
from .music_activity import MusicActivity
from .storage_activity import StorageActivity, StorageOperationType
from .task_activity import TaskActivity

# Define mapping of activity types to model classes for easy instantiation
ACTIVITY_TYPE_TO_MODEL = {
    ActivityType.MUSIC: MusicActivity,
    ActivityType.LOCATION: LocationActivity,
    ActivityType.TASK: TaskActivity,
    ActivityType.COLLABORATION: CollaborationActivity,
    ActivityType.STORAGE: StorageActivity,
    ActivityType.MEDIA: MediaActivity,
}


def get_model_class_for_activity_type(activity_type: ActivityType):
    """Get the model class for a specific activity type.

    Args:
        activity_type: The activity type.

    Returns:
        Type[ActivityData]: The model class for the activity type.
    """
    return ACTIVITY_TYPE_TO_MODEL.get(activity_type)
