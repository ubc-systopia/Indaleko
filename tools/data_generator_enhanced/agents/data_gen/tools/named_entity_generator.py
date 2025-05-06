"""
Enhanced named entity generator for Indaleko.

This module provides comprehensive named entity generation capabilities,
including people, organizations, places, and items with realistic attributes.
"""

import os
import sys
import random
import uuid
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Create mock SemanticAttributeRegistry for testing purposes
class SemanticAttributeRegistry:
    """Mock registry for semantic attributes."""
    
    # Common domains for attributes
    DOMAIN_STORAGE = "storage"
    DOMAIN_ACTIVITY = "activity"
    DOMAIN_SEMANTIC = "semantic"
    DOMAIN_RELATIONSHIP = "relationship"
    DOMAIN_MACHINE = "machine"
    DOMAIN_ENTITY = "entity"
    
    @classmethod
    def get_attribute_id(cls, domain: str, name: str) -> str:
        """Get an attribute ID for a registered attribute."""
        return f"{domain}_{name}_id"
    
    @classmethod
    def get_attribute_name(cls, attribute_id: str) -> str:
        """Get the human-readable name for an attribute ID."""
        return attribute_id.replace("_id", "")


# Create mock data models for testing purposes
class IndalekoBaseModel:
    """Mock base model for testing."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
    """Mock semantic attribute data model for testing."""
    pass

class IndalekoUUIDDataModel(IndalekoBaseModel):
    """Mock UUID data model for testing."""
    pass

class IndalekoLocationDataModel(IndalekoBaseModel):
    """Mock location data model for testing."""
    pass

class IndalekoNamedEntityType:
    """Entity types enumeration."""
    person = "person"
    organization = "organization"
    location = "location"
    date = "date"
    event = "event"
    product = "product"
    item = "item"
    keyword = "keyword"


class RelationshipManager:
    """Class to manage relationships between entities."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the relationship manager.
        
        Args:
            seed: Random seed for consistency
        """
        self.random = random.Random(seed)
        self.relationships = []
        
        # Define relationship types by entity pairs
        self.relationship_types = {
            # Person-to-person relationships
            ("person", "person"): [
                "family_member", "spouse", "sibling", "parent", "child",
                "friend", "colleague", "supervisor", "subordinate", "acquaintance"
            ],
            # Person-to-organization relationships
            ("person", "organization"): [
                "employee", "member", "customer", "owner", "investor",
                "founder", "contractor", "consultant", "board_member"
            ],
            # Person-to-location relationships
            ("person", "location"): [
                "resident", "visitor", "owner", "frequents", "works_at",
                "born_in", "travels_to"
            ],
            # Person-to-item relationships
            ("person", "item"): [
                "owns", "uses", "created", "purchased", "maintains",
                "likes", "dislikes"
            ],
            # Organization-to-organization relationships
            ("organization", "organization"): [
                "parent_company", "subsidiary", "partner", "competitor",
                "supplier", "customer", "investor", "alliance"
            ],
            # Organization-to-location relationships
            ("organization", "location"): [
                "headquarters", "branch", "service_area", "vendor_location",
                "event_venue"
            ],
            # Location-to-location relationships
            ("location", "location"): [
                "contains", "adjacent_to", "near", "part_of", "route_to"
            ]
        }
    
    def create_relationship(self, 
                           entity1: Dict[str, Any], 
                           entity2: Dict[str, Any],
                           relationship_type: Optional[str] = None) -> Dict[str, Any]:
        """Create a relationship between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            relationship_type: Optional specific relationship type
            
        Returns:
            Dictionary with relationship data
        """
        entity1_type = entity1["category"]
        entity2_type = entity2["category"]
        
        # Order the types to match our relationship_types keys
        type_pair = (entity1_type, entity2_type)
        reverse_pair = (entity2_type, entity1_type)
        
        # Determine direction and valid relationship types
        if type_pair in self.relationship_types:
            valid_types = self.relationship_types[type_pair]
            is_reversed = False
        elif reverse_pair in self.relationship_types:
            valid_types = self.relationship_types[reverse_pair]
            # Swap entities for reverse relationship
            entity1, entity2 = entity2, entity1
            entity1_type, entity2_type = entity2_type, entity1_type
            is_reversed = True
        else:
            # No defined relationship for this pair
            return None
        
        # Use provided type or select random
        rel_type = relationship_type if relationship_type else self.random.choice(valid_types)
        
        # Create relationship object
        relationship = {
            "Id": str(uuid.uuid4()),
            "entity1_id": entity1["Id"],
            "entity1_name": entity1["name"],
            "entity1_type": entity1_type,
            "relationship_type": rel_type,
            "entity2_id": entity2["Id"],
            "entity2_name": entity2["name"],
            "entity2_type": entity2_type,
            "confidence": self.random.uniform(0.7, 1.0),
            "is_reversed": is_reversed,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.relationships.append(relationship)
        return relationship


class EntityNameGenerator:
    """Class to generate realistic entity names based on type."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the name generator.
        
        Args:
            seed: Random seed for consistency
        """
        self.random = random.Random(seed)
        
        # First names data
        self.first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
            "William", "Elizabeth", "David", "Susan", "Richard", "Jessica", "Joseph", "Sarah", 
            "Thomas", "Karen", "Charles", "Nancy", "Daniel", "Lisa", "Matthew", "Margaret",
            "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley", "Steven", "Dorothy",
            "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna", "Kenneth", "Michelle",
            "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Timothy", "Deborah",
            "Jose", "Stephanie", "Gregory", "Rebecca", "Edward", "Laura", "Jason", "Helen",
            "Jeffrey", "Sharon", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
            "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Anna", "Stephen", "Ruth",
            "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Katherine",
            "Benjamin", "Samantha", "Samuel", "Christine", "Gregory", "Emma", "Alexander", "Catherine",
            "Frank", "Debra", "Patrick", "Virginia", "Raymond", "Rachel", "Jack", "Janet",
            "Dennis", "Maria", "Jerry", "Heather", "Tyler", "Diane", "Aaron", "Julie",
            "Jose", "Joyce", "Adam", "Victoria", "Nathan", "Kelly", "Henry", "Christina",
            "Douglas", "Lauren", "Zachary", "Joan", "Peter", "Evelyn", "Kyle", "Olivia",
            "Ethan", "Judith", "Walter", "Megan", "Noah", "Cheryl", "Jeremy", "Martha",
            "Christian", "Andrea", "Keith", "Frances", "Roger", "Hannah", "Terry", "Jacqueline",
            "Gerald", "Gloria", "Harold", "Ann", "Sean", "Teresa", "Austin", "Kathryn",
            "Carl", "Sara", "Arthur", "Janice", "Lawrence", "Jean", "Dylan", "Alice",
            "Jesse", "Madison", "Jordan", "Doris", "Bryan", "Abigail", "Billy", "Julia",
            "Joe", "Sophia", "Bruce", "Grace", "Gabriel", "Denise", "Logan", "Amber",
            "Albert", "Marilyn", "Willie", "Beverly", "Alan", "Danielle", "Juan", "Theresa",
            "Wayne", "Diana", "Elijah", "Brittany", "Randy", "Natalie", "Roy", "Sophia"
        ]
        
        # Last names data
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
            "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
            "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
            "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
            "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
            "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
            "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
            "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
            "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
            "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
            "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross",
            "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell", "Sullivan", "Bell"
        ]
        
        # Organization name components
        self.org_prefixes = [
            "Global", "Advanced", "United", "American", "Pacific", "National", "International",
            "Continental", "Digital", "Modern", "Future", "Premier", "Elite", "Dynamic",
            "Strategic", "Innovative", "Integrated", "Precision", "Reliable", "Secure",
            "First", "Quantum", "Allied", "Superior", "Universal", "Alpha", "Apex", "Peak",
            "Prime", "Omni", "Cyber", "Techno", "Meta", "Hyper", "Ultra", "Neo"
        ]
        
        self.org_roots = [
            "Tech", "Systems", "Solutions", "Dynamics", "Networks", "Industries", "Enterprises",
            "Communications", "Associates", "Consulting", "Services", "Partners", "Group",
            "Corporation", "International", "Innovations", "Resources", "Applications", "Data",
            "Computing", "Software", "Hardware", "Electronics", "Robotics", "Automation",
            "Logistics", "Financial", "Energy", "Healthcare", "Pharma", "Manufacturing",
            "Construction", "Development", "Properties", "Investments", "Insurance", "Media"
        ]
        
        self.org_suffixes = [
            "Inc", "LLC", "Ltd", "Group", "Co", "Corporation", "Associates", "Partners",
            "International", "Worldwide", "Holdings", "Ventures", "Capital", "Solutions",
            "Technologies", "Systems", "Networks", "Services", "Consultants", "Enterprises"
        ]
        
        # Location name components
        self.location_prefixes = [
            "North", "South", "East", "West", "New", "Old", "Upper", "Lower", "Central",
            "Downtown", "Uptown", "Midtown", "Riverside", "Lakeside", "Seaside", "Mountain",
            "Valley", "Highland", "Pleasant", "Green", "Golden", "Silver", "Royal", "Grand",
            "Fair", "Spring", "Summer", "Winter", "Autumn", "Crystal", "Pine", "Oak", "Cedar",
            "Forest", "Meadow", "Willow", "Brook", "River", "Lake", "Bay", "Harbor", "Cape"
        ]
        
        self.location_roots = [
            "town", "ville", "field", "wood", "ford", "port", "bridge", "haven", "burg",
            "view", "side", "dale", "grove", "hills", "shire", "ton", "land", "berg",
            "borough", "mouth", "water", "creek", "springs", "falls", "beach", "cliffs",
            "ridge", "valley", "summit", "park", "garden", "acres", "estates", "heights",
            "point", "island", "bay", "lake", "river", "creek", "trail", "way", "road"
        ]
        
        # Places/POI types
        self.place_types = [
            "restaurant", "cafe", "coffee shop", "bar", "pub", "nightclub", "hotel", "resort",
            "museum", "art gallery", "library", "bookstore", "theater", "cinema", "concert hall",
            "stadium", "arena", "gym", "fitness center", "spa", "salon", "barbershop",
            "shopping mall", "department store", "boutique", "supermarket", "grocery store",
            "bakery", "butcher", "farmer's market", "pharmacy", "hospital", "clinic", "dental office",
            "school", "college", "university", "daycare", "preschool", "park", "playground",
            "beach", "swimming pool", "basketball court", "tennis court", "golf course",
            "office building", "bank", "post office", "police station", "fire station", "city hall",
            "courthouse", "church", "temple", "mosque", "synagogue", "community center"
        ]
        
        # Item/product name components
        self.item_prefixes = [
            "Ultra", "Pro", "Max", "Super", "Mega", "Hyper", "Premium", "Elite", "Advanced",
            "Smart", "Intelligent", "Precision", "Digital", "Quantum", "Turbo", "Power", "Energy",
            "Eco", "Bio", "Natural", "Classic", "Vintage", "Retro", "Modern", "Sleek", "Slim",
            "Compact", "Portable", "Universal", "Multi", "All-in-One", "Deluxe", "Custom", "Special"
        ]
        
        self.item_roots = [
            "Book", "Laptop", "Phone", "Tablet", "Camera", "Watch", "TV", "Monitor", "Speaker",
            "Headphones", "Microphone", "Keyboard", "Mouse", "Printer", "Scanner", "Drone",
            "Console", "Controller", "Charger", "Cable", "Drive", "Card", "Chip", "Processor",
            "Memory", "Storage", "Battery", "Light", "Lamp", "Fan", "Heater", "Cooler",
            "Purifier", "Vacuum", "Washer", "Dryer", "Refrigerator", "Freezer", "Oven", "Stove",
            "Grill", "Toaster", "Blender", "Mixer", "Coffee Maker", "Kettle", "Iron", "Steamer",
            "Tool", "Drill", "Saw", "Hammer", "Wrench", "Screwdriver", "Pliers", "Level",
            "Bike", "Scooter", "Board", "Helmet", "Gloves", "Shoes", "Jacket", "Backpack", "Bag"
        ]
        
        self.item_suffixes = [
            "Pro", "Ultra", "Plus", "Max", "Premium", "Elite", "Deluxe", "Advanced", "Special",
            "Limited", "Edition", "Series", "Model", "Version", "Generation", "X", "S", "Z", "i",
            "Lite", "Mini", "Compact", "Portable", "Wireless", "Bluetooth", "USB", "HD", "4K",
            "Smart", "Connect", "Touch", "Flex", "Fold", "Slim", "Air", "Go", "Mobile", "One"
        ]
    
    def generate_person_name(self) -> str:
        """Generate a realistic person name.
        
        Returns:
            Person name string
        """
        first = self.random.choice(self.first_names)
        last = self.random.choice(self.last_names)
        return f"{first} {last}"
    
    def generate_organization_name(self) -> str:
        """Generate a realistic organization name.
        
        Returns:
            Organization name string
        """
        # Different organization name patterns
        pattern = self.random.randint(1, 3)
        
        if pattern == 1:
            # [Prefix] [Root] [Suffix]
            prefix = self.random.choice(self.org_prefixes)
            root = self.random.choice(self.org_roots)
            suffix = self.random.choice(self.org_suffixes)
            return f"{prefix} {root} {suffix}"
        elif pattern == 2:
            # [LastName] & [LastName] [Root/Suffix]
            name1 = self.random.choice(self.last_names)
            name2 = self.random.choice(self.last_names)
            while name1 == name2:
                name2 = self.random.choice(self.last_names)
            
            component = self.random.choice(self.org_roots + self.org_suffixes)
            return f"{name1} & {name2} {component}"
        else:
            # [LastName] [Root/Suffix]
            name = self.random.choice(self.last_names)
            component = self.random.choice(self.org_roots + self.org_suffixes)
            return f"{name} {component}"
    
    def generate_location_name(self) -> str:
        """Generate a realistic location name.
        
        Returns:
            Location name string
        """
        pattern = self.random.randint(1, 4)
        
        if pattern == 1:
            # [Prefix][Root] (no space)
            prefix = self.random.choice(self.location_prefixes)
            root = self.random.choice(self.location_roots)
            return f"{prefix}{root.capitalize()}"
        elif pattern == 2:
            # [Prefix] [Root]
            prefix = self.random.choice(self.location_prefixes)
            root = self.random.choice(self.location_roots)
            return f"{prefix} {root.capitalize()}"
        elif pattern == 3:
            # [LastName][Root] (no space)
            last_name = self.random.choice(self.last_names)
            root = self.random.choice(self.location_roots)
            return f"{last_name}{root.capitalize()}"
        else:
            # [LastName] [Root]
            last_name = self.random.choice(self.last_names)
            root = self.random.choice(self.location_roots)
            return f"{last_name} {root.capitalize()}"
    
    def generate_place_name(self) -> str:
        """Generate a realistic place name.
        
        Returns:
            Place name string
        """
        place_type = self.random.choice(self.place_types)
        
        # Different patterns for place names
        pattern = self.random.randint(1, 4)
        
        if pattern == 1:
            # The [Name]'s [PlaceType]
            name = self.random.choice(self.first_names)
            return f"The {name}'s {place_type.capitalize()}"
        elif pattern == 2:
            # [Name]'s [PlaceType]
            name = self.random.choice(self.first_names)
            return f"{name}'s {place_type.capitalize()}"
        elif pattern == 3:
            # The [Adjective] [PlaceType]
            adjective = self.random.choice(self.location_prefixes)
            return f"The {adjective} {place_type.capitalize()}"
        else:
            # [Location] [PlaceType]
            location = self.random.choice(self.location_prefixes)
            return f"{location} {place_type.capitalize()}"
    
    def generate_item_name(self) -> str:
        """Generate a realistic item/product name.
        
        Returns:
            Item name string
        """
        # Different item name patterns
        pattern = self.random.randint(1, 3)
        
        if pattern == 1:
            # [Prefix] [Root]
            prefix = self.random.choice(self.item_prefixes)
            root = self.random.choice(self.item_roots)
            return f"{prefix} {root}"
        elif pattern == 2:
            # [Root] [Suffix]
            root = self.random.choice(self.item_roots)
            suffix = self.random.choice(self.item_suffixes)
            return f"{root} {suffix}"
        else:
            # [Prefix] [Root] [Suffix]
            prefix = self.random.choice(self.item_prefixes)
            root = self.random.choice(self.item_roots)
            suffix = self.random.choice(self.item_suffixes)
            return f"{prefix} {root} {suffix}"


class EntityGenerator:
    """Class for generating different types of entities."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the entity generator.
        
        Args:
            seed: Random seed for consistency
        """
        self.random = random.Random(seed)
        self.name_generator = EntityNameGenerator(seed)
        self.relationship_manager = RelationshipManager(seed)
        
        # Store generated entities for reference
        self.entities = {
            "person": [],
            "organization": [],
            "location": [],
            "item": []
        }
        
        # Common locations that entities reference
        self.common_locations = {
            "home": None,
            "work": None,
            "school": None,
            "gym": None,
            "favorite_restaurant": None,
            "grocery_store": None
        }
        
        # Description templates for different entity types
        self.person_descriptions = [
            "A {age}-year-old {profession} who enjoys {hobby}",
            "{Role} at {organization} with expertise in {expertise}",
            "A {personality} individual who lives in {location}",
            "Born in {birth_place}, now working as a {profession}",
            "A {education} graduate specializing in {expertise}",
            "{Role} with {years} years of experience in {industry}"
        ]
        
        self.organization_descriptions = [
            "A {size} {type} specializing in {focus}",
            "Founded in {year}, provides {service} services",
            "Leading provider of {product} in the {industry} industry",
            "A {type} based in {location} with {employee_count} employees",
            "{Industry} {type} known for {reputation}",
            "Established in {year}, focuses on {focus} for {market} markets"
        ]
        
        self.location_descriptions = [
            "A {size} {type} located in {region}",
            "Known for its {feature}, this {type} is popular for {activity}",
            "Historic {type} established in {year}",
            "Scenic {type} with views of {landmark}",
            "Bustling {type} home to many {businesses}",
            "Quiet {type} ideal for {activity}"
        ]
        
        self.item_descriptions = [
            "A {condition} {color} {type} designed for {purpose}",
            "High-quality {material} {type} manufactured by {brand}",
            "Vintage {era} {type} with {feature}",
            "Premium {type} featuring {feature} technology",
            "Portable {type} perfect for {activity}",
            "Limited edition {type} with unique {feature}"
        ]
        
        # Content for filling in templates
        self.professions = [
            "software engineer", "doctor", "lawyer", "teacher", "accountant",
            "designer", "architect", "scientist", "writer", "marketing specialist",
            "project manager", "consultant", "analyst", "artist", "musician",
            "chef", "nurse", "therapist", "researcher", "sales representative"
        ]
        
        self.hobbies = [
            "photography", "hiking", "reading", "painting", "cooking",
            "gardening", "playing music", "traveling", "cycling", "yoga",
            "gaming", "woodworking", "knitting", "dancing", "collecting vinyl records",
            "rock climbing", "bird watching", "writing poetry", "watching movies", "running"
        ]
        
        self.roles = [
            "CEO", "CTO", "CFO", "Director", "VP", "Manager", "Team Lead",
            "Senior Engineer", "Principal Architect", "Head of Research",
            "Department Chair", "Founder", "Co-founder", "Partner", "Associate",
            "Specialist", "Coordinator", "Supervisor", "Administrator", "Analyst"
        ]
        
        self.expertise_areas = [
            "artificial intelligence", "data science", "cloud computing", "cybersecurity",
            "mobile development", "blockchain", "UX design", "digital marketing",
            "project management", "business analysis", "machine learning", "robotics",
            "bioinformatics", "renewable energy", "finance", "healthcare", "education",
            "international relations", "psychology", "environmental science"
        ]
        
        self.industries = [
            "technology", "healthcare", "finance", "education", "manufacturing",
            "retail", "hospitality", "entertainment", "transportation", "energy",
            "telecommunications", "consulting", "legal", "real estate", "construction",
            "agriculture", "aerospace", "automotive", "pharmaceuticals", "media"
        ]
        
        self.organization_types = [
            "company", "corporation", "firm", "startup", "enterprise",
            "agency", "consultancy", "institution", "foundation", "organization",
            "association", "cooperative", "partnership", "venture", "business",
            "practice", "group", "collective", "non-profit", "conglomerate"
        ]
        
        self.organization_sizes = [
            "small", "medium-sized", "large", "global", "multinational",
            "boutique", "emerging", "established", "leading", "prominent",
            "renowned", "prestigious", "influential", "growing", "expanding",
            "regional", "national", "international", "local", "specialized"
        ]
        
        self.organization_focuses = [
            "software development", "consulting services", "financial solutions",
            "healthcare innovation", "educational technology", "manufacturing excellence",
            "consumer products", "enterprise solutions", "data analytics", "creative services",
            "research and development", "customer experience", "logistics optimization",
            "digital transformation", "sustainability initiatives", "security services",
            "market research", "product design", "content creation", "business intelligence"
        ]
        
        self.location_types = [
            "city", "town", "village", "neighborhood", "district",
            "suburb", "metropolitan area", "community", "hamlet", "municipality",
            "borough", "settlement", "locality", "urban center", "county",
            "township", "precinct", "region", "territory", "zone"
        ]
        
        self.location_features = [
            "scenic waterfront", "historic architecture", "vibrant culture",
            "natural beauty", "diverse community", "thriving arts scene",
            "technology hub", "financial district", "educational institutions",
            "recreational facilities", "green spaces", "shopping districts",
            "culinary excellence", "nightlife", "historical significance",
            "annual festivals", "sports venues", "public transportation",
            "family-friendly environment", "affordable housing"
        ]
        
        self.location_activities = [
            "tourism", "outdoor recreation", "business", "education",
            "cultural events", "shopping", "dining", "entertainment",
            "sports", "relaxation", "artistic pursuits", "historical tours",
            "social gatherings", "community events", "nature exploration",
            "adventure activities", "wellness retreats", "culinary experiences",
            "educational workshops", "professional networking"
        ]
        
        self.item_types = [
            "smartphone", "laptop", "tablet", "smartwatch", "camera",
            "television", "speaker", "headphones", "gaming console", "drone",
            "refrigerator", "washing machine", "microwave", "vacuum cleaner", "air purifier",
            "furniture", "clothing", "accessory", "tool", "appliance"
        ]
        
        self.item_features = [
            "high-resolution display", "fast processor", "long battery life",
            "wireless connectivity", "water resistance", "voice control",
            "touch interface", "biometric security", "expandable storage",
            "modular design", "energy efficiency", "noise cancellation",
            "compact form factor", "durable construction", "premium materials",
            "smart functionality", "eco-friendly", "customizable options",
            "multi-purpose functionality", "intuitive controls"
        ]
        
        self.item_purposes = [
            "productivity", "entertainment", "communication", "creativity",
            "education", "fitness", "home improvement", "cooking", "cleaning",
            "organization", "security", "transportation", "recreation", "relaxation",
            "personal care", "health monitoring", "gaming", "photography", "music enjoyment",
            "outdoor activities"
        ]
        
        self.item_colors = [
            "black", "white", "silver", "gray", "blue",
            "red", "green", "yellow", "purple", "pink",
            "gold", "rose gold", "bronze", "copper", "titanium",
            "navy", "teal", "orange", "brown", "beige"
        ]
        
        self.item_conditions = [
            "new", "refurbished", "gently used", "vintage", "mint condition",
            "like-new", "certified pre-owned", "open-box", "collector's", "premium",
            "standard", "basic", "deluxe", "professional", "consumer-grade",
            "industrial-grade", "entry-level", "mid-range", "high-end", "top-of-the-line"
        ]
        
        self.item_materials = [
            "aluminum", "plastic", "glass", "stainless steel", "wood",
            "carbon fiber", "ceramic", "leather", "fabric", "silicone",
            "titanium", "composite", "rubber", "alloy", "crystal",
            "tempered glass", "nylon", "cotton", "polyester", "wool"
        ]
    
    def generate_entity(self, entity_type: str, count: int = 1) -> List[Dict[str, Any]]:
        """Generate entities of the specified type.
        
        Args:
            entity_type: Type of entity to generate
            count: Number of entities to generate
            
        Returns:
            List of generated entity dictionaries
        """
        entities = []
        
        for _ in range(count):
            if entity_type == "person":
                entity = self._generate_person()
            elif entity_type == "organization":
                entity = self._generate_organization()
            elif entity_type == "location":
                entity = self._generate_location()
            elif entity_type == "item":
                entity = self._generate_item()
            else:
                raise ValueError(f"Unsupported entity type: {entity_type}")
            
            # Store entity for reference
            self.entities[entity_type].append(entity)
            entities.append(entity)
        
        return entities
    
    def _generate_person(self) -> Dict[str, Any]:
        """Generate a person entity.
        
        Returns:
            Person entity dictionary
        """
        # Generate base entity data
        person_id = str(uuid.uuid4())
        name = self.name_generator.generate_person_name()
        
        # Fill in description template
        template = self.random.choice(self.person_descriptions)
        description = template.format(
            age=self.random.randint(18, 80),
            profession=self.random.choice(self.professions),
            hobby=self.random.choice(self.hobbies),
            organization=self._get_or_create_organization_name(),
            expertise=self.random.choice(self.expertise_areas),
            Role=self.random.choice(self.roles),
            location=self._get_or_create_location_name(),
            birth_place=self.name_generator.generate_location_name(),
            personality=self.random.choice(["friendly", "outgoing", "reserved", "analytical", "creative"]),
            education=self.random.choice(["Bachelor's", "Master's", "PhD", "High School", "Associate's"]),
            years=self.random.randint(1, 30),
            industry=self.random.choice(self.industries)
        )
        
        # Create entity
        entity = {
            "Id": person_id,
            "name": name,
            "category": IndalekoNamedEntityType.person,
            "description": description,
            "attributes": {
                "first_name": name.split()[0],
                "last_name": name.split()[1] if len(name.split()) > 1 else "",
                "profession": self.random.choice(self.professions),
                "age": self.random.randint(18, 80),
                "hobbies": [self.random.choice(self.hobbies) for _ in range(self.random.randint(1, 3))],
                "expertise": self.random.choice(self.expertise_areas)
            },
            "references": {
                "home": self._get_or_create_common_location("home"),
                "work": self._get_or_create_common_location("work"),
                "favorite_places": [
                    self._get_or_create_common_location(place) 
                    for place in self.random.sample(list(self.common_locations.keys())[2:], 
                                                 self.random.randint(1, 3))
                ]
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate semantic attributes
        entity["semantic_attributes"] = self._generate_person_semantic_attributes(entity)
        
        return entity
    
    def _generate_organization(self) -> Dict[str, Any]:
        """Generate an organization entity.
        
        Returns:
            Organization entity dictionary
        """
        # Generate base entity data
        org_id = str(uuid.uuid4())
        name = self.name_generator.generate_organization_name()
        
        # Fill in description template
        template = self.random.choice(self.organization_descriptions)
        description = template.format(
            size=self.random.choice(self.organization_sizes),
            type=self.random.choice(self.organization_types),
            focus=self.random.choice(self.organization_focuses),
            year=self.random.randint(1950, 2023),
            service=self.random.choice(self.organization_focuses),
            product=self.random.choice(["software", "hardware", "solutions", "services", "products"]),
            industry=self.random.choice(self.industries),
            location=self._get_or_create_location_name(),
            employee_count=self.random.choice(["50+", "100+", "500+", "1000+", "5000+", "10000+"]),
            reputation=self.random.choice(["innovation", "quality", "customer service", "reliability", "expertise"]),
            market=self.random.choice(["consumer", "enterprise", "small business", "government", "education", "healthcare"])
        )
        
        # Create entity
        entity = {
            "Id": org_id,
            "name": name,
            "category": IndalekoNamedEntityType.organization,
            "description": description,
            "attributes": {
                "industry": self.random.choice(self.industries),
                "size": self.random.choice(self.organization_sizes),
                "type": self.random.choice(self.organization_types),
                "founded": self.random.randint(1950, 2023),
                "focus": self.random.choice(self.organization_focuses)
            },
            "references": {
                "headquarters": self._get_or_create_location_name(),
                "key_people": [
                    self._get_or_create_person_name() 
                    for _ in range(self.random.randint(1, 3))
                ]
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate semantic attributes
        entity["semantic_attributes"] = self._generate_organization_semantic_attributes(entity)
        
        return entity
    
    def _generate_location(self) -> Dict[str, Any]:
        """Generate a location entity.
        
        Returns:
            Location entity dictionary
        """
        # Generate base entity data
        location_id = str(uuid.uuid4())
        name = self.name_generator.generate_location_name()
        
        # Fill in description template
        template = self.random.choice(self.location_descriptions)
        description = template.format(
            size=self.random.choice(["small", "medium-sized", "large", "sprawling", "compact"]),
            type=self.random.choice(self.location_types),
            region=self.random.choice(["the Pacific Northwest", "New England", "the Midwest", 
                                     "the South", "the West Coast", "the East Coast", 
                                     "Central Europe", "Western Europe", "Southeast Asia"]),
            feature=self.random.choice(self.location_features),
            activity=self.random.choice(self.location_activities),
            year=self.random.randint(1800, 2000),
            landmark=self.random.choice(["mountains", "ocean", "lake", "river", "forest", "desert"]),
            businesses=self.random.choice(["technology companies", "financial institutions", 
                                        "universities", "restaurants", "retail stores", 
                                        "entertainment venues"])
        )
        
        # Generate coordinates
        latitude = self.random.uniform(-90, 90)
        longitude = self.random.uniform(-180, 180)
        
        # Create entity
        entity = {
            "Id": location_id,
            "name": name,
            "category": IndalekoNamedEntityType.location,
            "description": description,
            "gis_location": {
                "source": "defined",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": latitude,
                "longitude": longitude
            },
            "attributes": {
                "type": self.random.choice(self.location_types),
                "features": [self.random.choice(self.location_features) for _ in range(self.random.randint(1, 3))],
                "activities": [self.random.choice(self.location_activities) for _ in range(self.random.randint(1, 3))],
                "population": self.random.choice(["small", "medium", "large", "very large"])
            },
            "references": {
                "nearby": [self.name_generator.generate_location_name() for _ in range(self.random.randint(1, 3))],
                "notable_places": [self.name_generator.generate_place_name() for _ in range(self.random.randint(1, 3))]
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate semantic attributes
        entity["semantic_attributes"] = self._generate_location_semantic_attributes(entity)
        
        return entity
    
    def _generate_item(self) -> Dict[str, Any]:
        """Generate an item entity.
        
        Returns:
            Item entity dictionary
        """
        # Generate base entity data
        item_id = str(uuid.uuid4())
        name = self.name_generator.generate_item_name()
        
        # Fill in description template
        template = self.random.choice(self.item_descriptions)
        description = template.format(
            condition=self.random.choice(self.item_conditions),
            color=self.random.choice(self.item_colors),
            type=self.random.choice(self.item_types),
            purpose=self.random.choice(self.item_purposes),
            material=self.random.choice(self.item_materials),
            brand=self.name_generator.generate_organization_name(),
            era=self.random.choice(["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s"]),
            feature=self.random.choice(self.item_features),
            activity=self.random.choice(self.item_purposes)
        )
        
        # Create entity
        entity = {
            "Id": item_id,
            "name": name,
            "category": IndalekoNamedEntityType.item,
            "description": description,
            "device_id": str(uuid.uuid4()),
            "attributes": {
                "type": self.random.choice(self.item_types),
                "color": self.random.choice(self.item_colors),
                "material": self.random.choice(self.item_materials),
                "condition": self.random.choice(self.item_conditions),
                "features": [self.random.choice(self.item_features) for _ in range(self.random.randint(1, 3))]
            },
            "references": {
                "manufacturer": self._get_or_create_organization_name(),
                "owner": self._get_or_create_person_name(),
                "location": self._get_or_create_common_location(
                    self.random.choice(["home", "work"]))
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate semantic attributes
        entity["semantic_attributes"] = self._generate_item_semantic_attributes(entity)
        
        return entity
    
    def _get_or_create_common_location(self, location_key: str) -> str:
        """Get or create a common location by key.
        
        Args:
            location_key: Key for the common location
            
        Returns:
            Location name
        """
        if self.common_locations[location_key] is None:
            if location_key == "home" or location_key == "work":
                self.common_locations[location_key] = self.name_generator.generate_location_name()
            else:
                self.common_locations[location_key] = self.name_generator.generate_place_name()
                
        return self.common_locations[location_key]
    
    def _get_or_create_organization_name(self) -> str:
        """Get an existing organization or create a new one.
        
        Returns:
            Organization name
        """
        if self.entities["organization"] and self.random.random() < 0.7:
            # 70% chance to use an existing organization
            return self.random.choice(self.entities["organization"])["name"]
        else:
            return self.name_generator.generate_organization_name()
    
    def _get_or_create_location_name(self) -> str:
        """Get an existing location or create a new one.
        
        Returns:
            Location name
        """
        if self.entities["location"] and self.random.random() < 0.7:
            # 70% chance to use an existing location
            return self.random.choice(self.entities["location"])["name"]
        else:
            return self.name_generator.generate_location_name()
    
    def _get_or_create_person_name(self) -> str:
        """Get an existing person or create a new one.
        
        Returns:
            Person name
        """
        if self.entities["person"] and self.random.random() < 0.7:
            # 70% chance to use an existing person
            return self.random.choice(self.entities["person"])["name"]
        else:
            return self.name_generator.generate_person_name()
    
    def _generate_person_semantic_attributes(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for a person entity.
        
        Args:
            entity: Person entity
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Add basic attributes
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_NAME"),
            "Value": entity["name"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_PROFESSION"),
            "Value": entity["attributes"]["profession"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_AGE"),
            "Value": entity["attributes"]["age"]
        })
        
        # Add hobby attributes
        for hobby in entity["attributes"]["hobbies"]:
            semantic_attributes.append({
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_HOBBY"),
                "Value": hobby
            })
        
        # Add location references
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_HOME"),
            "Value": entity["references"]["home"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "PERSON_WORKPLACE"),
            "Value": entity["references"]["work"]
        })
        
        return semantic_attributes
    
    def _generate_organization_semantic_attributes(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for an organization entity.
        
        Args:
            entity: Organization entity
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Add basic attributes
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ORGANIZATION_NAME"),
            "Value": entity["name"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ORGANIZATION_INDUSTRY"),
            "Value": entity["attributes"]["industry"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ORGANIZATION_TYPE"),
            "Value": entity["attributes"]["type"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ORGANIZATION_FOUNDED"),
            "Value": entity["attributes"]["founded"]
        })
        
        # Add location reference
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ORGANIZATION_HEADQUARTERS"),
            "Value": entity["references"]["headquarters"]
        })
        
        return semantic_attributes
    
    def _generate_location_semantic_attributes(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for a location entity.
        
        Args:
            entity: Location entity
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Add basic attributes
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "LOCATION_NAME"),
            "Value": entity["name"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "LOCATION_TYPE"),
            "Value": entity["attributes"]["type"]
        })
        
        # Add coordinates
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "LOCATION_LATITUDE"),
            "Value": entity["gis_location"]["latitude"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "LOCATION_LONGITUDE"),
            "Value": entity["gis_location"]["longitude"]
        })
        
        # Add features
        for feature in entity["attributes"]["features"]:
            semantic_attributes.append({
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ENTITY, "LOCATION_FEATURE"),
                "Value": feature
            })
        
        return semantic_attributes
    
    def _generate_item_semantic_attributes(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for an item entity.
        
        Args:
            entity: Item entity
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Add basic attributes
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_NAME"),
            "Value": entity["name"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_TYPE"),
            "Value": entity["attributes"]["type"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_COLOR"),
            "Value": entity["attributes"]["color"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_MATERIAL"),
            "Value": entity["attributes"]["material"]
        })
        
        # Add device ID
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_DEVICE_ID"),
            "Value": entity["device_id"]
        })
        
        # Add features
        for feature in entity["attributes"]["features"]:
            semantic_attributes.append({
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_FEATURE"),
                "Value": feature
            })
        
        # Add references
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_MANUFACTURER"),
            "Value": entity["references"]["manufacturer"]
        })
        
        semantic_attributes.append({
            "Identifier": SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ENTITY, "ITEM_OWNER"),
            "Value": entity["references"]["owner"]
        })
        
        return semantic_attributes


class NamedEntityGeneratorTool(Tool):
    """Tool to generate named entities and their relationships."""
    
    def __init__(self):
        """Initialize the named entity generator tool."""
        super().__init__(name="named_entity_generator", description="Generates named entities and relationships")
        
        # Initialize the entity generator
        self.entity_generator = EntityGenerator()
        
        # Initialize a relationship manager
        self.relationship_manager = RelationshipManager()
        
        # Set up a logger
        self.logger = logging.getLogger(__name__)
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the named entity generator tool.
        
        Args:
            params: Parameters for execution
                entity_counts: Dictionary with counts for each entity type
                relationship_density: Level of relationship density (0.0-1.0)
                truth_criteria: Optional criteria for truth entities
                common_locations: Optional dictionary of common locations
                
        Returns:
            Dictionary with generated entities and relationships
        """
        # Get parameters
        entity_counts = params.get("entity_counts", {
            "person": 5,
            "organization": 3,
            "location": 4,
            "item": 5
        })
        
        relationship_density = params.get("relationship_density", 0.5)
        truth_criteria = params.get("truth_criteria", {})
        seed = params.get("seed", None)
        
        # Set the random seed if provided
        if seed is not None:
            self.entity_generator = EntityGenerator(seed)
            self.relationship_manager = RelationshipManager(seed)
        
        # Set common locations if provided
        common_locations = params.get("common_locations", {})
        if common_locations:
            for key, value in common_locations.items():
                self.entity_generator.common_locations[key] = value
        
        # Generate entities
        entities = {
            "person": [],
            "organization": [],
            "location": [],
            "item": []
        }
        
        for entity_type, count in entity_counts.items():
            self.logger.info(f"Generating {count} {entity_type} entities")
            entities[entity_type] = self.entity_generator.generate_entity(entity_type, count)
        
        # Generate relationships based on density
        relationships = []
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        # Calculate how many relationships to generate based on density
        total_entity_pairs = len(all_entities) * (len(all_entities) - 1) // 2
        relationship_count = int(total_entity_pairs * relationship_density)
        
        # Generate relationships
        for _ in range(relationship_count):
            # Pick two random entities
            entity1 = random.choice(all_entities)
            entity2 = random.choice(all_entities)
            
            # Ensure they're different entities
            while entity1 == entity2:
                entity2 = random.choice(all_entities)
            
            # Try to create a relationship
            relationship = self.relationship_manager.create_relationship(entity1, entity2)
            if relationship:
                relationships.append(relationship)
        
        # Generate truth entities if criteria provided
        truth_entities = {}
        if truth_criteria:
            for entity_type, criteria in truth_criteria.items():
                if entity_type in entities:
                    # Create entity with specific criteria
                    truth_entity = self.entity_generator.generate_entity(entity_type, 1)[0]
                    
                    # Override properties based on criteria
                    for key, value in criteria.items():
                        if key in truth_entity:
                            truth_entity[key] = value
                        elif "attributes" in truth_entity and key in truth_entity["attributes"]:
                            truth_entity["attributes"][key] = value
                    
                    truth_entities[entity_type] = truth_entity
                    entities[entity_type].append(truth_entity)
        
        # Create the output
        result = {
            "entities": entities,
            "relationships": relationships,
            "truth_entities": truth_entities,
            "common_locations": self.entity_generator.common_locations
        }
        
        return result


# Add register method to the SemanticAttributeRegistry class
@classmethod
def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
    """Mock method to register an attribute."""
    return cls.get_attribute_id(domain, name)

# Add the method to the class
setattr(SemanticAttributeRegistry, 'register_attribute', register_attribute)


if __name__ == "__main__":
    # Simple test
    named_entity_generator = NamedEntityGeneratorTool()
    result = named_entity_generator.execute({
        "entity_counts": {
            "person": 3,
            "organization": 2,
            "location": 2,
            "item": 2
        },
        "relationship_density": 0.6,
        "seed": 42
    })
    
    import json
    
    # Custom JSON encoder for datetime and other complex types
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
    
    # Print the first person entity as a sample
    if result["entities"]["person"]:
        print("Sample Person Entity:")
        print(json.dumps(result["entities"]["person"][0], indent=2, cls=CustomEncoder))
    
    # Print a sample relationship
    if result["relationships"]:
        print("\nSample Relationship:")
        print(json.dumps(result["relationships"][0], indent=2, cls=CustomEncoder))