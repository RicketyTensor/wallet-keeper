import re
import xml.etree.ElementTree as ET
from typing import Dict


def get_namespace(element) -> str:
    m = re.match(r'\{.*\}', element.tag)
    return (m.group(0) if m else '').lstrip("{").rstrip("}")


def get_element(element: ET.Element, address: str, namespaces: Dict[str, str], empty: bool = False) -> ET.Element:
    """
    Get an element value

    :param element: xml element
    :param address: path to a subelement
    :param namespaces: dictionary of namespaces that are used in the address
    :param empty: flag to allow empty fields
    :return:
    """
    entry = element.find(address, namespaces)
    if entry is not None:
        return entry
    elif empty:
        return None
    else:
        resolved = address
        for key, ns in namespaces.items():
            resolved = resolved.replace(key + ":", "{" + ns + "}")
        raise AttributeError("{} doesn't include {}".format(element.tag, resolved))


def get_value(element: ET.Element, address: str, namespaces: Dict[str, str], empty: bool = False) -> str:
    """
    Get an element value

    :param element: xml element
    :param address: path to a subelement
    :param namespaces: dictionary of namespaces that are used in the address
    :param empty: flag to allow empty fields
    :return:
    """
    entry = get_element(element, address, namespaces, empty)
    if entry is not None:
        return entry.text
    else:
        return None



def get_attr(element: ET.Element, address: str, namespaces: Dict[str, str], attr: str) -> str:
    """
    Get an element value

    :param element: xml element
    :param address: path to a subelement
    :param namespaces: dictionary of namespaces that are used in the address
    :param attr: attribute name
    :return:
    """
    entry = get_element(element, address, namespaces)
    if attr in entry.attrib:
        return entry.attrib[attr]
    else:
        raise AttributeError("{} doesn't include the attribute {}".format(entry.tag, attr))
