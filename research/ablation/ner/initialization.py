"""Standard entity initialization for the ablation framework."""

import logging

from ..models.named_entity import EntityRelationType, EntityType, NamedEntity
from .enhanced_entity_manager import NamedEntityManager

logger = logging.getLogger(__name__)


class EntityInitializer:
    """Initializer for standard named entities.

    This class provides methods for initializing standard entities for
    testing and demonstration purposes.
    """

    def __init__(self, entity_manager: NamedEntityManager):
        """Initialize the entity initializer.

        Args:
            entity_manager: The entity manager to use for creating entities.
        """
        self.entity_manager = entity_manager

    def initialize_common_entities(self) -> dict[EntityType, dict[str, NamedEntity]]:
        """Initialize common entities for all entity types.

        This method creates standard entities for each entity type and
        sets up relationships between them.

        Returns:
            Dict[EntityType, Dict[str, NamedEntity]]: A dictionary of created entities by type and name.
        """
        # Create entities for each type
        created_entities = {entity_type: {} for entity_type in EntityType}

        # Initialize entities by type
        created_entities[EntityType.LOCATION].update(self.initialize_locations())
        created_entities[EntityType.PERSON].update(self.initialize_people())
        created_entities[EntityType.ORGANIZATION].update(self.initialize_organizations())
        created_entities[EntityType.EVENT].update(self.initialize_events())
        created_entities[EntityType.PRODUCT].update(self.initialize_products())
        created_entities[EntityType.WORK].update(self.initialize_works())
        created_entities[EntityType.TIME].update(self.initialize_time_entities())
        created_entities[EntityType.OTHER].update(self.initialize_other_entities())

        # Create relationships between entities
        self.initialize_relationships(created_entities)

        return created_entities

    def initialize_locations(self) -> dict[str, NamedEntity]:
        """Initialize location entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created location entities by name.
        """
        locations = {}

        # Countries
        countries = [
            ("United States", ["USA", "US", "United States of America"]),
            ("Canada", ["CA"]),
            ("United Kingdom", ["UK", "Great Britain"]),
            ("Australia", ["AU"]),
            ("Germany", ["DE"]),
            ("France", ["FR"]),
            ("Japan", ["JP"]),
            ("China", ["CN"]),
        ]

        for name, aliases in countries:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.LOCATION,
                name=name,
                aliases=aliases,
                properties={"type": "country"},
            )
            locations[name] = entity

        # US States
        us_states = [
            ("California", ["CA"]),
            ("New York", ["NY"]),
            ("Texas", ["TX"]),
            ("Florida", ["FL"]),
            ("Illinois", ["IL"]),
        ]

        for name, aliases in us_states:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.LOCATION,
                name=name,
                aliases=aliases,
                properties={"type": "state", "country": "United States"},
            )
            locations[name] = entity

        # Cities
        cities = [
            ("San Francisco", ["SF"], "California"),
            ("Los Angeles", ["LA"], "California"),
            ("New York City", ["NYC", "The Big Apple"], "New York"),
            ("Chicago", [], "Illinois"),
            ("Austin", [], "Texas"),
            ("Miami", [], "Florida"),
            ("London", [], "United Kingdom"),
            ("Paris", [], "France"),
            ("Tokyo", [], "Japan"),
            ("Sydney", [], "Australia"),
        ]

        for name, aliases, state in cities:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.LOCATION,
                name=name,
                aliases=aliases,
                properties={"type": "city", "state": state},
            )
            locations[name] = entity

        # Points of interest
        pois = [
            ("Golden Gate Bridge", [], "San Francisco"),
            ("Central Park", [], "New York City"),
            ("Eiffel Tower", [], "Paris"),
            ("Tokyo Tower", [], "Tokyo"),
            ("Sydney Opera House", [], "Sydney"),
        ]

        for name, aliases, city in pois:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.LOCATION,
                name=name,
                aliases=aliases,
                properties={"type": "point_of_interest", "city": city},
            )
            locations[name] = entity

        # Common places
        common_places = [
            ("Home", ["house"]),
            ("Work", ["office", "workplace"]),
            ("School", ["university", "college"]),
            ("Coffee Shop", ["cafe"]),
            ("Gym", ["fitness center"]),
            ("Park", []),
            ("Library", []),
            ("Airport", []),
            ("Restaurant", []),
            ("Mall", ["shopping center"]),
        ]

        for name, aliases in common_places:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.LOCATION,
                name=name,
                aliases=aliases,
                properties={"type": "common_place"},
            )
            locations[name] = entity

        return locations

    def initialize_people(self) -> dict[str, NamedEntity]:
        """Initialize person entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created person entities by name.
        """
        people = {}

        # Real people
        real_people = [
            ("Elon Musk", ["Elon"], {"occupation": "entrepreneur", "company": "Tesla"}),
            ("Bill Gates", ["Gates"], {"occupation": "entrepreneur", "company": "Microsoft"}),
            ("Taylor Swift", ["Swift"], {"occupation": "musician"}),
            ("Beyoncé", ["Queen B"], {"occupation": "musician"}),
            ("Barack Obama", ["Obama"], {"occupation": "politician"}),
        ]

        for name, aliases, properties in real_people:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.PERSON,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            people[name] = entity

        # Fictional people
        fictional_people = [
            ("John Smith", [], {"type": "fictional"}),
            ("Jane Doe", [], {"type": "fictional"}),
            ("Harry Potter", [], {"type": "fictional", "franchise": "Harry Potter"}),
            ("Luke Skywalker", [], {"type": "fictional", "franchise": "Star Wars"}),
            ("Tony Stark", ["Iron Man"], {"type": "fictional", "franchise": "Marvel"}),
        ]

        for name, aliases, properties in fictional_people:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.PERSON,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            people[name] = entity

        return people

    def initialize_organizations(self) -> dict[str, NamedEntity]:
        """Initialize organization entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created organization entities by name.
        """
        organizations = {}

        # Technology companies
        tech_companies = [
            ("Microsoft", ["MS"], {"industry": "technology", "location": "United States"}),
            ("Apple", [], {"industry": "technology", "location": "United States"}),
            ("Google", [], {"industry": "technology", "location": "United States"}),
            ("Amazon", [], {"industry": "technology", "location": "United States"}),
            ("Facebook", ["Meta"], {"industry": "technology", "location": "United States"}),
            ("Tesla", [], {"industry": "automotive", "location": "United States"}),
            ("Netflix", [], {"industry": "entertainment", "location": "United States"}),
            ("Twitter", ["X"], {"industry": "social media", "location": "United States"}),
            ("GitHub", [], {"industry": "technology", "location": "United States"}),
            ("Spotify", [], {"industry": "music", "location": "Sweden"}),
        ]

        for name, aliases, properties in tech_companies:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.ORGANIZATION,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            organizations[name] = entity

        # Other organizations
        other_organizations = [
            ("United Nations", ["UN"], {"type": "international"}),
            ("World Health Organization", ["WHO"], {"type": "international"}),
            ("University of California", ["UC"], {"type": "education"}),
            ("Stanford University", ["Stanford"], {"type": "education"}),
            ("Harvard University", ["Harvard"], {"type": "education"}),
        ]

        for name, aliases, properties in other_organizations:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.ORGANIZATION,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            organizations[name] = entity

        return organizations

    def initialize_events(self) -> dict[str, NamedEntity]:
        """Initialize event entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created event entities by name.
        """
        events = {}

        # Common events
        common_events = [
            ("Meeting", [], {"type": "common"}),
            ("Conference", [], {"type": "common"}),
            ("Workshop", [], {"type": "common"}),
            ("Birthday Party", ["Birthday"], {"type": "common"}),
            ("Wedding", [], {"type": "common"}),
            ("Concert", [], {"type": "common"}),
            ("Festival", [], {"type": "common"}),
            ("Exhibition", [], {"type": "common"}),
            ("Game", ["Match"], {"type": "common"}),
            ("Trip", ["Travel", "Journey"], {"type": "common"}),
        ]

        for name, aliases, properties in common_events:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.EVENT,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            events[name] = entity

        # Specific events
        specific_events = [
            ("CES", ["Consumer Electronics Show"], {"type": "specific", "category": "technology"}),
            ("WWDC", ["Worldwide Developers Conference"], {"type": "specific", "category": "technology"}),
            ("E3", ["Electronic Entertainment Expo"], {"type": "specific", "category": "gaming"}),
            ("Coachella", [], {"type": "specific", "category": "music"}),
            ("Olympics", ["Olympic Games"], {"type": "specific", "category": "sports"}),
        ]

        for name, aliases, properties in specific_events:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.EVENT,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            events[name] = entity

        return events

    def initialize_products(self) -> dict[str, NamedEntity]:
        """Initialize product entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created product entities by name.
        """
        products = {}

        # Technology products
        tech_products = [
            ("iPhone", [], {"category": "smartphone", "company": "Apple"}),
            ("iPad", [], {"category": "tablet", "company": "Apple"}),
            ("MacBook", [], {"category": "laptop", "company": "Apple"}),
            ("Surface", [], {"category": "laptop", "company": "Microsoft"}),
            ("Xbox", [], {"category": "gaming console", "company": "Microsoft"}),
            ("PlayStation", ["PS5", "PS4"], {"category": "gaming console", "company": "Sony"}),
            ("Pixel", [], {"category": "smartphone", "company": "Google"}),
            ("Galaxy", [], {"category": "smartphone", "company": "Samsung"}),
            ("Echo", ["Alexa"], {"category": "smart speaker", "company": "Amazon"}),
            ("Tesla Model 3", [], {"category": "car", "company": "Tesla"}),
        ]

        for name, aliases, properties in tech_products:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.PRODUCT,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            products[name] = entity

        # Software products
        software_products = [
            ("Windows", ["Windows 11", "Windows 10"], {"category": "operating system", "company": "Microsoft"}),
            ("macOS", ["macOS Ventura"], {"category": "operating system", "company": "Apple"}),
            ("iOS", [], {"category": "mobile operating system", "company": "Apple"}),
            ("Android", [], {"category": "mobile operating system", "company": "Google"}),
            ("Chrome", ["Google Chrome"], {"category": "web browser", "company": "Google"}),
            ("Safari", [], {"category": "web browser", "company": "Apple"}),
            ("Edge", ["Microsoft Edge"], {"category": "web browser", "company": "Microsoft"}),
            ("Office", ["Microsoft Office"], {"category": "productivity software", "company": "Microsoft"}),
            ("Photoshop", ["Adobe Photoshop"], {"category": "photo editing software", "company": "Adobe"}),
            ("Visual Studio Code", ["VS Code"], {"category": "code editor", "company": "Microsoft"}),
        ]

        for name, aliases, properties in software_products:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.PRODUCT,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            products[name] = entity

        return products

    def initialize_works(self) -> dict[str, NamedEntity]:
        """Initialize creative work entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created work entities by name.
        """
        works = {}

        # Movies
        movies = [
            ("Star Wars", ["Star Wars: A New Hope"], {"category": "movie", "franchise": "Star Wars"}),
            ("The Matrix", [], {"category": "movie"}),
            ("The Lord of the Rings", ["LOTR"], {"category": "movie", "franchise": "The Lord of the Rings"}),
            ("The Avengers", [], {"category": "movie", "franchise": "Marvel"}),
            ("Titanic", [], {"category": "movie"}),
        ]

        for name, aliases, properties in movies:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.WORK,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            works[name] = entity

        # Books
        books = [
            (
                "Harry Potter",
                ["Harry Potter and the Philosopher's Stone"],
                {"category": "book", "author": "J.K. Rowling"},
            ),
            ("The Great Gatsby", [], {"category": "book", "author": "F. Scott Fitzgerald"}),
            ("To Kill a Mockingbird", [], {"category": "book", "author": "Harper Lee"}),
            ("1984", [], {"category": "book", "author": "George Orwell"}),
            ("The Hobbit", [], {"category": "book", "author": "J.R.R. Tolkien"}),
        ]

        for name, aliases, properties in books:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.WORK,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            works[name] = entity

        # Music
        songs = [
            ("Bohemian Rhapsody", [], {"category": "song", "artist": "Queen"}),
            ("Thriller", [], {"category": "song", "artist": "Michael Jackson"}),
            ("Hey Jude", [], {"category": "song", "artist": "The Beatles"}),
            ("Imagine", [], {"category": "song", "artist": "John Lennon"}),
            ("Like a Rolling Stone", [], {"category": "song", "artist": "Bob Dylan"}),
        ]

        for name, aliases, properties in songs:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.WORK,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            works[name] = entity

        return works

    def initialize_time_entities(self) -> dict[str, NamedEntity]:
        """Initialize time entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created time entities by name.
        """
        time_entities = {}

        # Days of the week
        days = [
            ("Monday", [], {"type": "day_of_week", "order": "1"}),
            ("Tuesday", [], {"type": "day_of_week", "order": "2"}),
            ("Wednesday", [], {"type": "day_of_week", "order": "3"}),
            ("Thursday", [], {"type": "day_of_week", "order": "4"}),
            ("Friday", [], {"type": "day_of_week", "order": "5"}),
            ("Saturday", [], {"type": "day_of_week", "order": "6"}),
            ("Sunday", [], {"type": "day_of_week", "order": "7"}),
        ]

        for name, aliases, properties in days:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.TIME,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            time_entities[name] = entity

        # Months
        months = [
            ("January", ["Jan"], {"type": "month", "order": "1"}),
            ("February", ["Feb"], {"type": "month", "order": "2"}),
            ("March", ["Mar"], {"type": "month", "order": "3"}),
            ("April", ["Apr"], {"type": "month", "order": "4"}),
            ("May", [], {"type": "month", "order": "5"}),
            ("June", ["Jun"], {"type": "month", "order": "6"}),
            ("July", ["Jul"], {"type": "month", "order": "7"}),
            ("August", ["Aug"], {"type": "month", "order": "8"}),
            ("September", ["Sep", "Sept"], {"type": "month", "order": "9"}),
            ("October", ["Oct"], {"type": "month", "order": "10"}),
            ("November", ["Nov"], {"type": "month", "order": "11"}),
            ("December", ["Dec"], {"type": "month", "order": "12"}),
        ]

        for name, aliases, properties in months:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.TIME,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            time_entities[name] = entity

        # Time periods
        periods = [
            ("Morning", [], {"type": "time_of_day"}),
            ("Afternoon", [], {"type": "time_of_day"}),
            ("Evening", [], {"type": "time_of_day"}),
            ("Night", [], {"type": "time_of_day"}),
            ("Yesterday", [], {"type": "relative_day"}),
            ("Today", [], {"type": "relative_day"}),
            ("Tomorrow", [], {"type": "relative_day"}),
            ("Last Week", [], {"type": "relative_week"}),
            ("This Week", [], {"type": "relative_week"}),
            ("Next Week", [], {"type": "relative_week"}),
            ("Last Month", [], {"type": "relative_month"}),
            ("This Month", [], {"type": "relative_month"}),
            ("Next Month", [], {"type": "relative_month"}),
            ("Last Year", [], {"type": "relative_year"}),
            ("This Year", [], {"type": "relative_year"}),
            ("Next Year", [], {"type": "relative_year"}),
        ]

        for name, aliases, properties in periods:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.TIME,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            time_entities[name] = entity

        return time_entities

    def initialize_other_entities(self) -> dict[str, NamedEntity]:
        """Initialize other types of entities.

        Returns:
            Dict[str, NamedEntity]: A dictionary of created entities by name.
        """
        other_entities = {}

        # Genres
        genres = [
            ("Rock", [], {"category": "music_genre"}),
            ("Pop", [], {"category": "music_genre"}),
            ("Hip Hop", ["Rap"], {"category": "music_genre"}),
            ("Classical", [], {"category": "music_genre"}),
            ("Jazz", [], {"category": "music_genre"}),
            ("Country", [], {"category": "music_genre"}),
            ("Electronic", ["EDM"], {"category": "music_genre"}),
            ("R&B", ["Rhythm and Blues"], {"category": "music_genre"}),
            ("Metal", [], {"category": "music_genre"}),
            ("Folk", [], {"category": "music_genre"}),
        ]

        for name, aliases, properties in genres:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.OTHER,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            other_entities[name] = entity

        # Programming languages
        languages = [
            ("Python", [], {"category": "programming_language"}),
            ("JavaScript", ["JS"], {"category": "programming_language"}),
            ("Java", [], {"category": "programming_language"}),
            ("C++", [], {"category": "programming_language"}),
            ("C#", ["CSharp"], {"category": "programming_language"}),
            ("Ruby", [], {"category": "programming_language"}),
            ("Go", ["Golang"], {"category": "programming_language"}),
            ("Swift", [], {"category": "programming_language"}),
            ("PHP", [], {"category": "programming_language"}),
            ("TypeScript", ["TS"], {"category": "programming_language"}),
        ]

        for name, aliases, properties in languages:
            entity = self.entity_manager.create_entity(
                entity_type=EntityType.OTHER,
                name=name,
                aliases=aliases,
                properties=properties,
            )
            other_entities[name] = entity

        return other_entities

    def initialize_relationships(self, entities: dict[EntityType, dict[str, NamedEntity]]) -> None:
        """Initialize relationships between entities.

        Args:
            entities: A dictionary of entities by type and name.
        """
        # Country -> State relationships
        if "United States" in entities[EntityType.LOCATION]:
            usa = entities[EntityType.LOCATION]["United States"]

            for state_name in ["California", "New York", "Texas", "Florida", "Illinois"]:
                if state_name in entities[EntityType.LOCATION]:
                    state = entities[EntityType.LOCATION][state_name]
                    self.entity_manager.create_relation(
                        usa.id,
                        state.id,
                        EntityRelationType.PARENT,
                        {"type": "country-state"},
                    )

        # State -> City relationships
        for state_name, city_names in [
            ("California", ["San Francisco", "Los Angeles"]),
            ("New York", ["New York City"]),
            ("Illinois", ["Chicago"]),
            ("Texas", ["Austin"]),
            ("Florida", ["Miami"]),
        ]:
            if state_name in entities[EntityType.LOCATION]:
                state = entities[EntityType.LOCATION][state_name]

                for city_name in city_names:
                    if city_name in entities[EntityType.LOCATION]:
                        city = entities[EntityType.LOCATION][city_name]
                        self.entity_manager.create_relation(
                            state.id,
                            city.id,
                            EntityRelationType.PARENT,
                            {"type": "state-city"},
                        )

        # City -> Point of Interest relationships
        for city_name, poi_names in [
            ("San Francisco", ["Golden Gate Bridge"]),
            ("New York City", ["Central Park"]),
            ("Paris", ["Eiffel Tower"]),
            ("Tokyo", ["Tokyo Tower"]),
            ("Sydney", ["Sydney Opera House"]),
        ]:
            if city_name in entities[EntityType.LOCATION]:
                city = entities[EntityType.LOCATION][city_name]

                for poi_name in poi_names:
                    if poi_name in entities[EntityType.LOCATION]:
                        poi = entities[EntityType.LOCATION][poi_name]
                        self.entity_manager.create_relation(
                            city.id,
                            poi.id,
                            EntityRelationType.PARENT,
                            {"type": "city-poi"},
                        )

        # Company -> Product relationships
        for company_name, product_names in [
            ("Apple", ["iPhone", "iPad", "MacBook", "macOS", "iOS", "Safari"]),
            ("Microsoft", ["Surface", "Xbox", "Windows", "Edge", "Office", "Visual Studio Code"]),
            ("Google", ["Pixel", "Android", "Chrome"]),
            ("Amazon", ["Echo"]),
            ("Tesla", ["Tesla Model 3"]),
        ]:
            if company_name in entities[EntityType.ORGANIZATION]:
                company = entities[EntityType.ORGANIZATION][company_name]

                for product_name in product_names:
                    if product_name in entities[EntityType.PRODUCT]:
                        product = entities[EntityType.PRODUCT][product_name]
                        self.entity_manager.create_relation(
                            company.id,
                            product.id,
                            EntityRelationType.CREATED_BY,
                            {"type": "company-product"},
                        )

        # Company -> Person relationships
        for person_name, company_name in [
            ("Elon Musk", "Tesla"),
            ("Bill Gates", "Microsoft"),
        ]:
            if person_name in entities[EntityType.PERSON] and company_name in entities[EntityType.ORGANIZATION]:
                person = entities[EntityType.PERSON][person_name]
                company = entities[EntityType.ORGANIZATION][company_name]

                self.entity_manager.create_relation(
                    person.id,
                    company.id,
                    EntityRelationType.OWNS,
                    {"type": "person-company"},
                )

        # Franchise -> Works relationships
        franchises = {
            "Star Wars": ["Star Wars"],
            "Harry Potter": ["Harry Potter"],
            "The Lord of the Rings": ["The Lord of the Rings"],
            "Marvel": ["The Avengers"],
        }

        for franchise_name, work_names in franchises.items():
            # Create a franchise entity if it doesn't exist
            franchise = None
            for work_name in work_names:
                if work_name in entities[EntityType.WORK]:
                    work = entities[EntityType.WORK][work_name]

                    # Create franchise entity if needed
                    if franchise is None:
                        franchise = self.entity_manager.create_entity(
                            entity_type=EntityType.OTHER,
                            name=franchise_name,
                            properties={"category": "franchise"},
                        )

                    # Create relationship
                    self.entity_manager.create_relation(
                        franchise.id,
                        work.id,
                        EntityRelationType.PARENT,
                        {"type": "franchise-work"},
                    )

        # Adjacent day relationships
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for i in range(len(days) - 1):
            if days[i] in entities[EntityType.TIME] and days[i + 1] in entities[EntityType.TIME]:
                day1 = entities[EntityType.TIME][days[i]]
                day2 = entities[EntityType.TIME][days[i + 1]]

                self.entity_manager.create_relation(
                    day1.id,
                    day2.id,
                    EntityRelationType.RELATED,
                    {"type": "adjacent_day"},
                )

        # Connection between Sunday and Monday
        if "Sunday" in entities[EntityType.TIME] and "Monday" in entities[EntityType.TIME]:
            sunday = entities[EntityType.TIME]["Sunday"]
            monday = entities[EntityType.TIME]["Monday"]

            self.entity_manager.create_relation(
                sunday.id,
                monday.id,
                EntityRelationType.RELATED,
                {"type": "adjacent_day"},
            )

        # Adjacent month relationships
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        for i in range(len(months) - 1):
            if months[i] in entities[EntityType.TIME] and months[i + 1] in entities[EntityType.TIME]:
                month1 = entities[EntityType.TIME][months[i]]
                month2 = entities[EntityType.TIME][months[i + 1]]

                self.entity_manager.create_relation(
                    month1.id,
                    month2.id,
                    EntityRelationType.RELATED,
                    {"type": "adjacent_month"},
                )

        # Connection between December and January
        if "December" in entities[EntityType.TIME] and "January" in entities[EntityType.TIME]:
            december = entities[EntityType.TIME]["December"]
            january = entities[EntityType.TIME]["January"]

            self.entity_manager.create_relation(
                december.id,
                january.id,
                EntityRelationType.RELATED,
                {"type": "adjacent_month"},
            )


def initialize_standard_entities(db: object | None = None) -> NamedEntityManager:
    """Initialize standard entities and return the entity manager.

    Args:
        db: The database connection. If None, only in-memory entities will be used.

    Returns:
        NamedEntityManager: The entity manager with initialized entities.
    """
    # Create entity manager
    entity_manager = NamedEntityManager(db=db)

    # Create entity initializer
    initializer = EntityInitializer(entity_manager)

    # Initialize entities
    initializer.initialize_common_entities()

    return entity_manager
