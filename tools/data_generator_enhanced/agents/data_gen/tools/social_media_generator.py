"""
Enhanced social media activity generator for Indaleko.

This module provides comprehensive social media activity generation capabilities,
including posts, comments, likes, and shares with associated metadata.
"""

import os
import sys
import random
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta
import json
import math

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Import generators
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import (
    EntityNameGenerator, IndalekoNamedEntityType
)

# Import semantic attribute registry and data models
try:
    # Try to import real registry and data models
    from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
    from data_models.base import IndalekoBaseModel
    from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
    from data_models.i_uuid import IndalekoUUIDDataModel
    from db.db_collections import IndalekoDBCollections
    from db.db_config import IndalekoDBConfig
    HAS_DB = True
except ImportError:
    # Create mock registry and data models for testing
    HAS_DB = False
    
    class SemanticAttributeRegistry:
        """Mock registry for semantic attributes."""
        
        # Common domains for attributes
        DOMAIN_STORAGE = "storage"
        DOMAIN_ACTIVITY = "activity"
        DOMAIN_SEMANTIC = "semantic"
        DOMAIN_RELATIONSHIP = "relationship"
        DOMAIN_MACHINE = "machine"
        DOMAIN_ENTITY = "entity"
        DOMAIN_SOCIAL = "social"
        
        @classmethod
        def get_attribute_id(cls, domain: str, name: str) -> str:
            """Get an attribute ID for a registered attribute."""
            return f"{domain}_{name}_id"
        
        @classmethod
        def get_attribute_name(cls, attribute_id: str) -> str:
            """Get the human-readable name for an attribute ID."""
            return attribute_id.replace("_id", "")
        
        @classmethod
        def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
            """Register an attribute."""
            return cls.get_attribute_id(domain, name)
    
    class IndalekoBaseModel:
        """Mock base model for testing."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self):
            """Convert model to dictionary."""
            return self.__dict__
    
    class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
        """Mock semantic attribute data model for testing."""
        pass
    
    class IndalekoUUIDDataModel(IndalekoBaseModel):
        """Mock UUID data model for testing."""
        pass


class Post:
    """Class representing a social media post with rich metadata."""
    
    def __init__(self, 
                post_id: str, 
                user_id: str,
                platform: str,
                text: str,
                hashtags: List[str],
                creation_time: datetime,
                location_data: Optional[Dict[str, Any]] = None,
                media_refs: Optional[List[str]] = None,
                mentioned_entities: Optional[List[Dict[str, Any]]] = None):
        """Initialize a post.
        
        Args:
            post_id: Unique identifier for the post
            user_id: User who created the post
            platform: Social media platform (Instagram, Twitter, etc.)
            text: Post content text
            hashtags: List of hashtags
            creation_time: Time the post was created
            location_data: Optional location data
            media_refs: Optional list of media reference IDs
            mentioned_entities: Optional list of mentioned entities
        """
        self.post_id = post_id
        self.user_id = user_id
        self.platform = platform
        self.text = text
        self.hashtags = hashtags
        self.creation_time = creation_time
        self.location_data = location_data
        self.media_refs = media_refs if media_refs else []
        self.mentioned_entities = mentioned_entities if mentioned_entities else []
        self.comments = []
        self.likes = []
        self.shares = []
    
    def add_comment(self, comment: Dict[str, Any]) -> None:
        """Add a comment to the post.
        
        Args:
            comment: Comment data
        """
        self.comments.append(comment)
    
    def add_like(self, like: Dict[str, Any]) -> None:
        """Add a like to the post.
        
        Args:
            like: Like data
        """
        self.likes.append(like)
    
    def add_share(self, share: Dict[str, Any]) -> None:
        """Add a share to the post.
        
        Args:
            share: Share data
        """
        self.shares.append(share)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the post to a dictionary.
        
        Returns:
            Dictionary representation of the post
        """
        return {
            "Id": self.post_id,
            "UserId": self.user_id,
            "Platform": self.platform,
            "Text": self.text,
            "Hashtags": self.hashtags,
            "CreationTime": self.creation_time.isoformat(),
            "LocationData": self.location_data,
            "MediaRefs": self.media_refs,
            "MentionedEntities": self.mentioned_entities,
            "Comments": self.comments,
            "Likes": self.likes,
            "Shares": self.shares,
            "Engagement": {
                "CommentCount": len(self.comments),
                "LikeCount": len(self.likes),
                "ShareCount": len(self.shares)
            }
        }


class SocialMediaActivityGenerator:
    """Generator for realistic social media activity."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        self.name_generator = EntityNameGenerator(seed)
        
        # Social media platforms
        self.platforms = ["Instagram", "Twitter", "Facebook", "LinkedIn", "TikTok"]
        
        # Content generation templates
        self.post_templates = [
            "Just had a great {meal} at {restaurant}! {hashtags}",
            "Visited {location} today! Amazing views. {hashtags}",
            "Working on {project} with {person}. Making progress! {hashtags}",
            "Checking out the new {product} from {company}. {opinion} {hashtags}",
            "Just finished reading {book}. {opinion} {hashtags}",
            "Happy birthday to {person}! Have an amazing day! {hashtags}",
            "Excited to announce that I'm now working with {company}! {hashtags}",
            "Just went to {event} at {location}. {opinion} {hashtags}",
            "New {object} just arrived! Can't wait to try it out. {hashtags}",
            "Celebrating {milestone} today! {hashtags}",
            "Throwback to when we visited {location} last year. {hashtags}",
            "Enjoying some {activity} on this beautiful day. {hashtags}",
            "Just watched {movie}. {opinion} {hashtags}",
            "Morning {activity} with {person}. Perfect start to the day! {hashtags}",
            "Looking forward to {event} next week! Anyone else going? {hashtags}",
            "Need recommendations for {category} in {location}. Any suggestions? {hashtags}",
            "Feeling {emotion} today. {hashtags}",
            "Just completed {achievement}! Feeling accomplished. {hashtags}",
            "New profile pic! Photo taken by {person} at {location}. {hashtags}",
            "Can't believe it's already been {time_period} since {event}. {hashtags}"
        ]
        
        self.comment_templates = [
            "Great post! {additional}",
            "Love this! {additional}",
            "Looks amazing! {additional}",
            "Thanks for sharing! {additional}",
            "Couldn't agree more! {additional}",
            "Wow! {additional}",
            "This is awesome! {additional}",
            "Congrats! {additional}",
            "So happy for you! {additional}",
            "Well deserved! {additional}",
            "This made my day! {additional}",
            "Fantastic! {additional}",
            "So true! {additional}",
            "I was just thinking about this! {additional}",
            "Perfect timing! {additional}"
        ]
        
        self.comment_additions = [
            "",
            "Keep it up!",
            "Looking forward to more!",
            "We should catch up soon!",
            "Miss you!",
            "Hope all is well!",
            "Let's do this again sometime!",
            "So proud of you!",
            "This reminds me of our trip last year.",
            "Can you share more details?",
            "This is exactly what I needed today.",
            "You always post the best content!",
            "This made me smile."
        ]
        
        # Fill-in content for templates
        self.meals = ["dinner", "lunch", "breakfast", "brunch", "snack", "dessert", "coffee"]
        self.restaurants = ["The Local Bistro", "Flavor Express", "Ocean View", "Green Garden", 
                          "City Diner", "The Rustic Table", "Fusion Kitchen", "Spice Route",
                          "Cafe Central", "Sweet Delights", "Mountain Brew", "Harvest Table"]
        
        self.locations = ["the beach", "downtown", "the mountains", "the park", "the lake", 
                        "the museum", "the art gallery", "the zoo", "the aquarium", 
                        "Paris", "New York", "Tokyo", "London", "Barcelona", "Sydney",
                        "San Francisco", "Rome", "Venice", "Amsterdam", "Berlin"]
        
        self.projects = ["a new website", "a mobile app", "a research paper", "a painting", 
                       "a new recipe", "home renovations", "a garden project", 
                       "a photography series", "a podcast episode", "a business plan"]
        
        self.products = ["smartphone", "laptop", "camera", "headphones", "smartwatch", 
                       "fitness tracker", "coffee maker", "blender", "electric car", 
                       "drone", "VR headset", "robot vacuum", "smart speaker"]
        
        self.companies = ["Apple", "Google", "Microsoft", "Amazon", "Tesla", "Samsung", 
                        "Sony", "Nike", "Adidas", "Starbucks", "McDonald's", "Coca-Cola",
                        "Pepsi", "Disney", "Netflix", "Spotify", "Adobe", "IBM"]
        
        self.books = ["The Great Gatsby", "To Kill a Mockingbird", "Pride and Prejudice", 
                     "1984", "The Hobbit", "Harry Potter", "The Alchemist", 
                     "The Da Vinci Code", "The Hunger Games", "The Shining",
                     "The Catcher in the Rye", "Brave New World", "Lord of the Rings"]
        
        self.events = ["concert", "conference", "workshop", "festival", "wedding", 
                     "graduation", "exhibition", "game", "race", "party", 
                     "fundraiser", "seminar", "meetup", "hackathon", "premiere"]
        
        self.objects = ["book", "gadget", "tool", "furniture", "clothing", "artwork", 
                      "jewelry", "plant", "toy", "kitchenware", "electronic",
                      "game", "collectible", "instrument", "sports equipment"]
        
        self.milestones = ["anniversary", "birthday", "graduation", "promotion", 
                         "retirement", "engagement", "wedding", "new job", 
                         "new home", "achievement", "award", "certification"]
        
        self.activities = ["yoga", "running", "hiking", "cycling", "swimming", 
                         "meditation", "painting", "cooking", "reading", 
                         "gardening", "photography", "dancing", "gaming"]
        
        self.movies = ["The Godfather", "Star Wars", "The Matrix", "Avatar", 
                     "Titanic", "Inception", "The Dark Knight", "Forrest Gump", 
                     "The Lion King", "Jaws", "E.T.", "Jurassic Park",
                     "Toy Story", "The Avengers", "Frozen", "Finding Nemo"]
        
        self.emotions = ["happy", "excited", "grateful", "inspired", "peaceful", 
                       "motivated", "reflective", "energized", "relaxed", 
                       "blessed", "content", "optimistic", "accomplished"]
        
        self.achievements = ["a marathon", "a course", "a degree", "a certification", 
                           "a project", "a goal", "a challenge", "a milestone", 
                           "a personal best", "a promotion", "an award"]
        
        self.time_periods = ["a year", "two years", "three months", "six months", 
                           "a week", "a month", "five years", "a decade"]
        
        self.categories = ["restaurants", "hotels", "activities", "shops", 
                         "gyms", "parks", "museums", "galleries", "cafes", 
                         "bars", "theaters", "cinemas", "bookstores"]
        
        self.opinions = [
            "Loving it so far!",
            "Highly recommended!",
            "Not sure about it yet.",
            "It's amazing!",
            "Exceeds expectations!",
            "Worth every penny!",
            "It's changed my life!",
            "So impressed!",
            "Mind blown!",
            "Can't recommend it enough!",
            "Kind of disappointed honestly.",
            "Mixed feelings about this one.",
            "Game changer!",
            "Better than expected!"
        ]
        
        # Common hashtags by category
        self.hashtag_categories = {
            "lifestyle": ["#lifestyle", "#life", "#happy", "#love", "#instagood", "#photooftheday", 
                        "#beautiful", "#fashion", "#style", "#instadaily"],
            "travel": ["#travel", "#travelgram", "#instatravel", "#wanderlust", "#adventure", 
                     "#explore", "#vacation", "#holiday", "#trip", "#tourism", "#traveling"],
            "food": ["#food", "#foodporn", "#instafood", "#foodie", "#delicious", "#yummy", 
                   "#breakfast", "#lunch", "#dinner", "#nom", "#foodgasm", "#foodstagram"],
            "fitness": ["#fitness", "#workout", "#gym", "#fit", "#health", "#healthy", "#training", 
                      "#exercise", "#strong", "#motivation", "#fitspo", "#fitfam"],
            "technology": ["#tech", "#technology", "#innovation", "#gadget", "#apple", "#smartphone", 
                         "#laptop", "#computer", "#coding", "#programming", "#developer", "#software"],
            "nature": ["#nature", "#naturephotography", "#outdoors", "#landscape", "#sky", "#sunset", 
                     "#sun", "#sunrise", "#flowers", "#mountains", "#beach", "#sea", "#ocean"],
            "art": ["#art", "#artist", "#artwork", "#creative", "#drawing", "#painting", 
                  "#illustration", "#design", "#sketch", "#artistic", "#creativity", "#paint"],
            "books": ["#books", "#book", "#reading", "#read", "#bookstagram", "#literature", 
                    "#author", "#bookworm", "#bookish", "#booklover", "#bibliophile"],
            "movies": ["#movies", "#movie", "#film", "#cinema", "#actor", "#actress", "#director", 
                     "#hollywood", "#netflix", "#series", "#tv", "#show"],
            "music": ["#music", "#song", "#singer", "#musician", "#band", "#concert", 
                    "#guitar", "#piano", "#vocals", "#rock", "#pop", "#hiphop", "#rap"],
            "business": ["#business", "#entrepreneur", "#success", "#motivation", "#startup", 
                       "#inspiration", "#entrepreneurship", "#marketing", "#leadership", "#goals"],
            "education": ["#education", "#learning", "#student", "#study", "#school", "#college", 
                        "#university", "#knowledge", "#teacher", "#learn", "#academy"],
            "pets": ["#pet", "#pets", "#dog", "#cat", "#puppy", "#kitten", "#animal", 
                   "#dogstagram", "#catstagram", "#instadog", "#instacat", "#animals", "#love"],
            "fashion": ["#fashion", "#style", "#outfit", "#ootd", "#clothes", "#clothing", 
                      "#fashionista", "#streetstyle", "#trendy", "#model", "#beauty", "#makeup"],
            "gaming": ["#gaming", "#gamer", "#game", "#videogames", "#ps5", "#xbox", 
                     "#nintendo", "#twitch", "#streamer", "#esports", "#pc", "#console"],
            "sports": ["#sports", "#sport", "#football", "#soccer", "#basketball", "#baseball", 
                     "#hockey", "#tennis", "#golf", "#running", "#fitness", "#workout"]
        }
        
        # Generate some random people for mentions
        self.people = [self.name_generator.generate_person_name() for _ in range(20)]
    
    def generate_posts(self, 
                      count: int, 
                      user_id: str,
                      start_time: datetime,
                      end_time: datetime,
                      platforms: Optional[List[str]] = None,
                      entities: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                      media_refs: Optional[List[str]] = None,
                      location_data: Optional[List[Dict[str, Any]]] = None) -> List[Post]:
        """Generate social media posts.
        
        Args:
            count: Number of posts to generate
            user_id: User ID for the posts
            start_time: Start time range for posts
            end_time: End time range for posts
            platforms: Optional specific platforms to use
            entities: Optional dict of entity lists by type
            media_refs: Optional media references to attach
            location_data: Optional location data to use
            
        Returns:
            List of generated posts
        """
        if not platforms:
            platforms = self.platforms
            
        if not entities:
            entities = {}
            
        if not media_refs:
            media_refs = []
            
        posts = []
        
        for _ in range(count):
            # Choose a platform
            platform = self.random.choice(platforms)
            
            # Generate a creation time within the range
            time_range = (end_time - start_time).total_seconds()
            random_seconds = self.random.uniform(0, time_range)
            creation_time = start_time + timedelta(seconds=random_seconds)
            
            # Generate post text with associated metadata
            post_data = self._generate_post_text(platform)
            text = post_data["text"]
            hashtags = post_data["hashtags"]
            
            # Gather mentioned entities
            mentioned_entities = []
            
            # Add people mentions
            if "person" in entities and entities["person"] and self.random.random() < 0.6:
                num_mentions = self.random.randint(1, min(3, len(entities["person"])))
                for person in self.random.sample(entities["person"], num_mentions):
                    mentioned_entities.append({
                        "id": person["Id"],
                        "name": person["name"],
                        "type": "person"
                    })
            else:
                # Use random people if no entities provided
                if self.random.random() < 0.3:
                    num_mentions = self.random.randint(1, 2)
                    for person in self.random.sample(self.people, num_mentions):
                        mentioned_entities.append({
                            "id": str(uuid.uuid4()),
                            "name": person,
                            "type": "person"
                        })
            
            # Add location mention
            post_location = None
            if location_data and self.random.random() < 0.4:
                location = self.random.choice(location_data)
                post_location = {
                    "latitude": location.get("latitude", 0),
                    "longitude": location.get("longitude", 0),
                    "name": location.get("name", "Unnamed Location"),
                    "timestamp": creation_time.isoformat()
                }
            
            # Attach media references?
            post_media_refs = []
            if media_refs and self.random.random() < 0.7:
                num_media = min(self.random.randint(1, 3), len(media_refs))
                post_media_refs = self.random.sample(media_refs, num_media)
            
            # Create the post
            post_id = str(uuid.uuid4())
            post = Post(
                post_id=post_id,
                user_id=user_id,
                platform=platform,
                text=text,
                hashtags=hashtags,
                creation_time=creation_time,
                location_data=post_location,
                media_refs=post_media_refs,
                mentioned_entities=mentioned_entities
            )
            
            # Add engagement
            self._add_engagement(post, entities)
            
            posts.append(post)
            
        # Sort posts by creation time
        posts.sort(key=lambda p: p.creation_time)
        
        return posts
    
    def _generate_post_text(self, platform: str) -> Dict[str, Any]:
        """Generate text for a social media post.
        
        Args:
            platform: Platform to generate for
            
        Returns:
            Dictionary with text and hashtags
        """
        template = self.random.choice(self.post_templates)
        
        # Determine maximum post length based on platform
        max_length = 280 if platform == "Twitter" else 2200
        
        # Select hashtag categories and count based on platform
        if platform == "Instagram":
            hashtag_count = self.random.randint(3, 12)
            categories = self.random.sample(list(self.hashtag_categories.keys()), self.random.randint(2, 5))
        elif platform == "Twitter":
            hashtag_count = self.random.randint(1, 5)
            categories = self.random.sample(list(self.hashtag_categories.keys()), self.random.randint(1, 3))
        elif platform == "LinkedIn":
            hashtag_count = self.random.randint(2, 6)
            business_categories = ["business", "technology", "education"]
            other_categories = self.random.sample([c for c in self.hashtag_categories.keys() if c not in business_categories], self.random.randint(1, 3))
            categories = business_categories + other_categories
        else:
            hashtag_count = self.random.randint(2, 8)
            categories = self.random.sample(list(self.hashtag_categories.keys()), self.random.randint(1, 4))
        
        # Gather hashtags
        all_hashtags = []
        for category in categories:
            category_hashtags = self.hashtag_categories.get(category, [])
            if category_hashtags:
                count = min(self.random.randint(1, 4), len(category_hashtags))
                all_hashtags.extend(self.random.sample(category_hashtags, count))
        
        # Limit to hashtag_count
        if len(all_hashtags) > hashtag_count:
            all_hashtags = self.random.sample(all_hashtags, hashtag_count)
        
        # Fill in the template
        text = template.format(
            meal=self.random.choice(self.meals),
            restaurant=self.random.choice(self.restaurants),
            location=self.random.choice(self.locations),
            project=self.random.choice(self.projects),
            person=self.random.choice(self.people),
            product=self.random.choice(self.products),
            company=self.random.choice(self.companies),
            book=self.random.choice(self.books),
            opinion=self.random.choice(self.opinions),
            event=self.random.choice(self.events),
            object=self.random.choice(self.objects),
            milestone=self.random.choice(self.milestones),
            activity=self.random.choice(self.activities),
            movie=self.random.choice(self.movies),
            emotion=self.random.choice(self.emotions),
            achievement=self.random.choice(self.achievements),
            time_period=self.random.choice(self.time_periods),
            category=self.random.choice(self.categories),
            hashtags=""
        )
        
        # Check if we have room for hashtags within max_length
        remaining_space = max_length - len(text)
        
        # Add hashtags if there's room
        if remaining_space > 0:
            # Format hashtags as a string
            hashtag_text = " ".join(all_hashtags[:min(len(all_hashtags), int(remaining_space / 12))])
            text = template.format(
                meal=self.random.choice(self.meals),
                restaurant=self.random.choice(self.restaurants),
                location=self.random.choice(self.locations),
                project=self.random.choice(self.projects),
                person=self.random.choice(self.people),
                product=self.random.choice(self.products),
                company=self.random.choice(self.companies),
                book=self.random.choice(self.books),
                opinion=self.random.choice(self.opinions),
                event=self.random.choice(self.events),
                object=self.random.choice(self.objects),
                milestone=self.random.choice(self.milestones),
                activity=self.random.choice(self.activities),
                movie=self.random.choice(self.movies),
                emotion=self.random.choice(self.emotions),
                achievement=self.random.choice(self.achievements),
                time_period=self.random.choice(self.time_periods),
                category=self.random.choice(self.categories),
                hashtags=hashtag_text
            )
        
        return {
            "text": text,
            "hashtags": all_hashtags
        }
    
    def _add_engagement(self, post: Post, entities: Dict[str, List[Dict[str, Any]]]) -> None:
        """Add engagement (comments, likes, shares) to a post.
        
        Args:
            post: Post to add engagement to
            entities: Available entities to use for engagement
        """
        # Determine engagement level based on platform
        if post.platform == "Instagram":
            comments_count = self._weighted_random([0, 1, 2, 3, 5, 8, 13], [0.1, 0.2, 0.3, 0.2, 0.1, 0.06, 0.04])
            likes_count = self._weighted_random([0, 1, 3, 5, 10, 20, 50], [0.05, 0.1, 0.25, 0.3, 0.2, 0.08, 0.02])
            shares_count = 0  # Instagram doesn't have shares
        elif post.platform == "Twitter":
            comments_count = self._weighted_random([0, 1, 2, 3, 5, 8], [0.2, 0.3, 0.25, 0.15, 0.07, 0.03])
            likes_count = self._weighted_random([0, 1, 2, 5, 10, 20], [0.1, 0.2, 0.3, 0.25, 0.1, 0.05])
            shares_count = self._weighted_random([0, 1, 2, 3, 5], [0.3, 0.4, 0.2, 0.07, 0.03])
        elif post.platform == "Facebook":
            comments_count = self._weighted_random([0, 1, 2, 3, 5, 8], [0.15, 0.25, 0.3, 0.15, 0.1, 0.05])
            likes_count = self._weighted_random([0, 1, 2, 5, 10, 20, 30], [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05])
            shares_count = self._weighted_random([0, 1, 2, 3], [0.7, 0.2, 0.07, 0.03])
        else:
            # Default values for other platforms
            comments_count = self._weighted_random([0, 1, 2, 3], [0.4, 0.3, 0.2, 0.1])
            likes_count = self._weighted_random([0, 1, 2, 5, 10], [0.2, 0.3, 0.3, 0.15, 0.05])
            shares_count = self._weighted_random([0, 1], [0.8, 0.2])
        
        # Add comments
        for _ in range(comments_count):
            comment = self._generate_comment()
            post.add_comment(comment)
        
        # Add likes
        for _ in range(likes_count):
            like = {"user_id": str(uuid.uuid4()), "timestamp": self._get_later_time(post.creation_time).isoformat()}
            post.add_like(like)
        
        # Add shares
        for _ in range(shares_count):
            share = {"user_id": str(uuid.uuid4()), "timestamp": self._get_later_time(post.creation_time).isoformat()}
            post.add_share(share)
    
    def _generate_comment(self) -> Dict[str, Any]:
        """Generate a comment.
        
        Returns:
            Comment data as a dictionary
        """
        template = self.random.choice(self.comment_templates)
        addition = self.random.choice(self.comment_additions)
        
        text = template.format(additional=addition)
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=self.random.randint(1, 1440))
        
        return {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "text": text,
            "timestamp": timestamp.isoformat()
        }
    
    def _get_later_time(self, base_time: datetime) -> datetime:
        """Get a random time that is later than the base time.
        
        Args:
            base_time: Base time
            
        Returns:
            Later time
        """
        minutes_later = self.random.randint(1, 1440)  # Up to 24 hours later
        return base_time + timedelta(minutes=minutes_later)
    
    def _weighted_random(self, values: List[Any], weights: List[float]) -> Any:
        """Get a random value according to weights.
        
        Args:
            values: List of possible values
            weights: List of weights corresponding to the values
            
        Returns:
            Randomly selected value
        """
        return self.random.choices(values, weights=weights, k=1)[0]


class SocialMediaActivityGeneratorTool(Tool):
    """Tool to generate realistic social media activity data."""
    
    def __init__(self):
        """Initialize the social media activity generator tool."""
        super().__init__(name="social_media_generator", description="Generates realistic social media activity data")
        
        # Create the activity generator
        self.generator = SocialMediaActivityGenerator()
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connection if available
        self.db_config = None
        self.db = None
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
                self.logger.info("Database connection initialized")
            except Exception as e:
                self.logger.error(f"Error initializing database connection: {e}")
        
        # Register social media semantic attributes
        self._register_social_media_attributes()
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the social media activity generator tool.
        
        Args:
            params: Parameters for execution
                count: Number of posts to generate
                criteria: Criteria for generation
                    user_id: User identifier
                    platforms: Optional list of platforms to generate for
                    start_time: Optional start time for posts
                    end_time: Optional end time for posts
                    entities: Optional dict of entity lists by type
                    media_refs: Optional list of media references
                    location_data: Optional list of location data
                    
        Returns:
            Dictionary with generated records
        """
        count = params.get("count", 5)
        criteria = params.get("criteria", {})
        
        user_id = criteria.get("user_id", str(uuid.uuid4()))
        platforms = criteria.get("platforms", None)
        
        # Default time range: last 90 days to now
        now = datetime.now(timezone.utc)
        start_time = criteria.get("start_time", now - timedelta(days=90))
        end_time = criteria.get("end_time", now)
        
        # Convert timestamps to datetime if needed
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time, timezone.utc)
        if isinstance(end_time, (int, float)):
            end_time = datetime.fromtimestamp(end_time, timezone.utc)
            
        # Get named entities if provided
        entities = criteria.get("entities", {})
        
        # Get media references (e.g., EXIF image IDs)
        media_refs = criteria.get("media_refs", [])
        
        # If we have database access and no media refs provided, try to fetch some
        if HAS_DB and self.db and not media_refs:
            self.logger.info("No media references provided, trying to fetch from database")
            media_refs = self._fetch_media_refs(count * 2)  # Get 2x the count to have choices
        
        # Get location data
        location_data = criteria.get("location_data", [])
        
        # Generate posts
        posts = self.generator.generate_posts(
            count=count,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            platforms=platforms,
            entities=entities,
            media_refs=media_refs,
            location_data=location_data
        )
        
        # Convert posts to dictionaries and add semantic attributes
        post_records = []
        for post in posts:
            post_dict = post.to_dict()
            post_dict["SemanticAttributes"] = self._generate_semantic_attributes(post)
            post_records.append(post_dict)
            
            # Store in database if available
            if HAS_DB and self.db:
                self._store_social_media_record(post_dict)
        
        return {
            "records": post_records
        }
    
    def _register_social_media_attributes(self) -> None:
        """Register social media semantic attributes."""
        # Platform attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "PLATFORM", 
            "a8f5a7b3-c9d8-4e6f-9a1b-2c3d4e5f6a7b"
        )
        
        # Post type attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "POST_TYPE", 
            "b9e8d7c6-f5e4-3d2c-1b0a-9f8e7d6c5b4a"
        )
        
        # Hashtag attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "HASHTAG", 
            "c1b2a3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
        )
        
        # Mention attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "MENTION", 
            "d2c3b4a5-f6e7-8d9c-0b1a-2f3e4d5c6b7a"
        )
        
        # Location attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "LOCATION", 
            "e3d4c5b6-a7f8-9e0d-1c2b-3a4f5e6d7c8b"
        )
        
        # Media reference attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "MEDIA_REF", 
            "f4e5d6c7-b8a9-0f1e-2d3c-4b5a6f7e8d9c"
        )
        
        # Engagement attribute
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SOCIAL, 
            "ENGAGEMENT", 
            "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
        )
    
    def _generate_semantic_attributes(self, post: Post) -> List[Dict[str, Any]]:
        """Generate semantic attributes for a social media post.
        
        Args:
            post: Post to generate attributes for
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Platform attribute
        platform_attr = IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SOCIAL, "PLATFORM"),
                Label="PLATFORM"
            ),
            Value=post.platform
        )
        semantic_attributes.append(platform_attr.model_dump())
        
        # Post type attribute (based on media presence)
        post_type = "text"
        if post.media_refs:
            post_type = "media"
        
        post_type_attr = IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SOCIAL, "POST_TYPE"),
                Label="POST_TYPE"
            ),
            Value=post_type
        )
        semantic_attributes.append(post_type_attr.model_dump())
        
        # Hashtag attributes
        for hashtag in post.hashtags:
            hashtag_attr = IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_SOCIAL, "HASHTAG"),
                    Label="HASHTAG"
                ),
                Value=hashtag
            )
            semantic_attributes.append(hashtag_attr.model_dump())
        
        # Mention attributes
        for entity in post.mentioned_entities:
            mention_attr = IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_SOCIAL, "MENTION"),
                    Label="MENTION"
                ),
                Value=entity["name"]
            )
            semantic_attributes.append(mention_attr.model_dump())
        
        # Location attribute
        if post.location_data:
            location_name = post.location_data.get("name", "")
            if location_name:
                location_attr = IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SOCIAL, "LOCATION"),
                        Label="LOCATION"
                    ),
                    Value=location_name
                )
                semantic_attributes.append(location_attr.model_dump())
        
        # Media reference attributes
        for media_ref in post.media_refs:
            media_attr = IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_SOCIAL, "MEDIA_REF"),
                    Label="MEDIA_REF"
                ),
                Value=media_ref
            )
            semantic_attributes.append(media_attr.model_dump())
        
        # Engagement attribute (aggregate)
        engagement_level = "low"
        total_engagement = len(post.comments) + len(post.likes) + len(post.shares)
        
        if total_engagement > 20:
            engagement_level = "high"
        elif total_engagement > 5:
            engagement_level = "medium"
        
        engagement_attr = IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_SOCIAL, "ENGAGEMENT"),
                Label="ENGAGEMENT"
            ),
            Value=engagement_level
        )
        semantic_attributes.append(engagement_attr.model_dump())
        
        return semantic_attributes
    
    def _fetch_media_refs(self, count: int) -> List[str]:
        """Fetch media references from the database.
        
        Args:
            count: Number of media references to fetch
            
        Returns:
            List of media reference IDs
        """
        # Query for the ExifData collection to find media with EXIF data
        refs = []
        
        if not self.db:
            return refs
            
        try:
            query = """
            FOR doc IN @@collection
            LIMIT @count
            RETURN doc.Object
            """
            
            cursor = self.db.aql.execute(
                query,
                bind_vars={
                    "@collection": IndalekoDBCollections.Indaleko_SemanticData_Collection,
                    "count": count
                }
            )
            
            refs = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(refs)} media references from database")
            
        except Exception as e:
            self.logger.error(f"Error fetching media references: {e}")
            
        return refs
    
    def _store_social_media_record(self, record: Dict[str, Any]) -> bool:
        """Store a social media record in the database.
        
        Args:
            record: Social media record to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
            
        try:
            # Define collection name for social media activity
            collection_name = "SocialMediaActivity"
            
            # Check if collection exists, create if not
            if not self.db.has_collection(collection_name):
                self.logger.info(f"Creating SocialMediaActivity collection")
                self.db.create_collection(collection_name)
            
            # Get the collection
            collection = self.db.collection(collection_name)
            
            # Insert the record
            collection.insert(record)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing social media record: {e}")
            return False


if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    tool = SocialMediaActivityGeneratorTool()
    
    # Create a test entity
    test_entity = {
        "Id": str(uuid.uuid4()),
        "name": "John Smith",
        "category": IndalekoNamedEntityType.person
    }
    
    test_location = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "San Francisco"
    }
    
    result = tool.execute({
        "count": 3,
        "criteria": {
            "user_id": "test_user",
            "platforms": ["Instagram", "Twitter"],
            "entities": {
                "person": [test_entity]
            },
            "location_data": [test_location]
        }
    })
    
    # Print sample post
    if result["records"]:
        sample = result["records"][0].copy()
        
        if "SemanticAttributes" in sample:
            sample["SemanticAttributes"] = f"[{len(sample['SemanticAttributes'])} attributes]"
        
        print(json.dumps(sample, indent=2))