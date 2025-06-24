import os
import xml.etree.ElementTree as ET
from typing import List, Dict

def generate_xml_annotations(annotations: List[Dict], output_path: str) -> None:
    """Generate an ASAP compatible XML file from annotations.

    Parameters
    ----------
    annotations : list of dict
        Each dict must contain a key ``"coords"`` with a list of ``(x, y)``
        tuples describing the polygon vertices.  An optional ``"class"`` key is
        ignored but kept for compatibility.
    output_path : str
        Destination path of the XML file.
    """
    root = ET.Element("ASAP_Annotations")
    node_annotations = ET.SubElement(root, "Annotations")
    ET.SubElement(root, "AnnotationGroups")

    for idx, ann in enumerate(annotations):
        attrs = {
            "Name": f"Annotation {idx}",
            "Type": "Polygon",
            "PartOfGroup": "None",
            "Color": "0,255,0",
        }
        node_annotation = ET.SubElement(node_annotations, "Annotation", attrs)
        node_coords = ET.SubElement(node_annotation, "Coordinates")
        for order, (x, y) in enumerate(ann.get("coords", [])):
            ET.SubElement(
                node_coords,
                "Coordinate",
                {
                    "Order": str(order),
                    "X": str(int(x)),
                    "Y": str(int(y)),
                },
            )

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def read_xml_annotations(path: str) -> List[Dict]:
    """Load annotations from an ASAP XML file if it exists."""
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    anns = []
    for node in tree.findall('./Annotations/Annotation'):
        coords = []
        coord_node = node.find('Coordinates')
        if coord_node is None:
            continue
        for c in coord_node.findall('Coordinate'):
            x = float(c.get('X', '0'))
            y = float(c.get('Y', '0'))
            coords.append((x, y))
        anns.append({'coords': coords, 'class': node.get('PartOfGroup', 'gland')})
    return anns


from shapely.geometry import Polygon
from shapely.validation import make_valid


def simplify_polygon(vertices, tolerance=5.0):
    """Return simplified polygon coordinates using the given tolerance."""
    poly = Polygon(vertices)
    simplified = poly.simplify(tolerance, preserve_topology=True)
    if not simplified.is_valid:
        simplified = make_valid(simplified)
    if isinstance(simplified, Polygon):
        return list(simplified.exterior.coords)
    return []
