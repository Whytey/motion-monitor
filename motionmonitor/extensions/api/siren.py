from abc import ABC


class SubEntity(ABC):
    pass


class Entity:
    def __init__(self, classes=[]):
        self._class: [str] = classes
        self._title: str = None
        self._links: [Link] = []
        self._actions: [Action] = []
        self._properties: dict = {}
        self._entities: [SubEntity] = []

    @property
    def properties(self):
        return self.properties

    @properties.setter
    def properties(self, properties):
        self._properties = properties

    def set_property(self, name: str, value):
        self._properties[name] = value

    def append_link(self, relationship: str, href: str):
        self._links.append({"rel": relationship, "href": href})

    def add_sub_entity(self, sub_entity: SubEntity):
        self._entities.append(sub_entity)

    def to_json(self):
        response = {}
        if self._class:
            response["class"] = self._class

        if self._links:
            response["links"] = self._links

        if self._actions:
            response["actions"] = self._actions

        if self._properties:
            response["properties"] = self._properties

        if self._entities:
            response["entities"] = []
            for entity in self._entities:
                response["entities"].append(entity.to_json())
        return response


class EmbeddedLinkSubEntity(SubEntity):
    def __init__(self, rel, href, classes=[], media_type=None, title=None):
        self._class: [str] = classes
        self._rel: [RelValue] = rel
        self._href: str = href
        self._type: MediaType = media_type
        self._title: title


class EmbeddedRepresentationSubEntity(Entity, SubEntity):
    def __init__(self, rel, classes=[]):
        super().__init__(classes)
        self._rel: [RelValue] = rel
        self._entity: Entity = None

    def to_json(self):
        response = super().to_json()
        response["rel"] = self._rel
        return response


class Action:
    def __init__(self):
        self._class: [str] = []
        self._name: str = None
        self._method: str = "GET"
        self._href: str = None
        self._title: str = None
        self._type: str = "application/x-www-form-urlencoded"
        self._fields: [Field] = None


class Field:
    def __init__(self):
        self._name: str = None
        self._type: str = None
        self._title: str = None
        self._value: str = None


class Link:
    def __init__(self):
        self._class: [str] = None
        self._title: str = None
        self._rel: [RelValue] = []
        self._href: str = None
        self._type: MediaType = None


class RelValue:
    def __init__(self):
        self._value: str = None


class MediaType:
    def __init__(self):
        self._value: str = None
