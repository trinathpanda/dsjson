"""Define-XML parser for dsjson (Final Version)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import xml.etree.ElementTree as ET

from dsjson.logging_config import get_logger
from dsjson.exceptions import (
    DefineXMLParseError,
    DefineXMLDomainNotFoundError,
)

logger = get_logger()


class DefineXMLParser:
    """Parser for CDISC Define-XML → Dataset-JSON column metadata."""

    def __init__(self, define_path: Union[str, Path]):
        self.define_path = Path(define_path)

        if not self.define_path.exists():
            raise FileNotFoundError(f"Define-XML not found: {define_path}")

        self.tree: Optional[ET.ElementTree] = None
        self.root: Optional[ET.Element] = None
        self.ns: Dict[str, str] = {}

    # ---------------------------------------------------------------------
    # Core parsing
    # ---------------------------------------------------------------------

    def parse(self) -> None:
        """Parse Define-XML file and load namespaces."""
        try:
            logger.info("Parsing Define-XML: %s", self.define_path)

            self.tree = ET.parse(self.define_path)
            self.root = self.tree.getroot()
            self.ns = self._extract_namespaces()

            logger.info(
                "Define-XML parsed successfully (namespaces=%s)",
                ",".join(self.ns.keys())
            )

        except Exception as e:
            logger.exception("Define-XML parsing failed: %s", str(e))
            raise DefineXMLParseError(str(self.define_path), str(e)) from e

    def _extract_namespaces(self) -> Dict[str, str]:
        """Extract XML namespaces dynamically."""
        namespaces: Dict[str, str] = {}
        for _, elem in ET.iterparse(str(self.define_path), events=["start-ns"]):
            prefix, uri = elem
            namespaces[prefix if prefix else "odm"] = uri
        return namespaces

    # ---------------------------------------------------------------------
    # Domain extraction
    # ---------------------------------------------------------------------

    def get_domains(self) -> List[str]:
        """Return list of SDTM domains."""
        if self.root is None:
            raise RuntimeError("Define-XML not parsed. Call parse() first.")

        domains: List[str] = []

        for itemgroup in self.root.findall(".//odm:ItemGroupDef", self.ns):
            # Define-XML 1.0 has no Domain attribute; fall back to Name
            domain = itemgroup.attrib.get("Domain") or itemgroup.attrib.get("Name")
            if domain:
                domains.append(domain)

        logger.info("Domains detected: %d", len(domains))
        return domains

    def get_dataset_names(self) -> List[str]:
        """Return the Name of every ItemGroupDef (dataset), e.g. DM, AE, SUPPAE."""
        if self.root is None:
            raise RuntimeError("Define-XML not parsed. Call parse() first.")

        return [
            ig.attrib["Name"].upper()
            for ig in self.root.findall(".//odm:ItemGroupDef", self.ns)
            if ig.attrib.get("Name")
        ]

    def get_domain(self, domain: str) -> ET.Element:
        """Return ItemGroupDef node for a dataset (matched on Name, then Domain)."""
        if self.root is None:
            raise RuntimeError("Define-XML not parsed. Call parse() first.")

        dom = domain.upper()
        itemgroups = self.root.findall(".//odm:ItemGroupDef", self.ns)

        # Name first: SUPP--/split datasets share the parent's Domain value
        for attr in ("Name", "Domain"):
            for itemgroup in itemgroups:
                if (itemgroup.attrib.get(attr) or "").upper() == dom:
                    return itemgroup

        raise DefineXMLDomainNotFoundError(domain)

    def get_item_group_oid(self, domain: str) -> Optional[str]:
        """OID of the dataset's ItemGroupDef, e.g. "IG.DM" or "DM"."""
        return self.get_domain(domain).attrib.get("OID")

    def _get_domain_keys(self, node: ET.Element) -> List[str]:
        """Key variables from def:DomainKeys (Define-XML 1.0), e.g. "STUDYID, USUBJID"."""
        if "def" not in self.ns:
            return []
        keys = node.attrib.get(f"{{{self.ns['def']}}}DomainKeys") or ""
        return [k.strip().upper() for k in keys.split(",") if k.strip()]

    def _get_label(self, node: ET.Element) -> Optional[str]:
        """Label from Description/TranslatedText (Define 2.x) or def:Label (Define 1.0)."""
        desc = node.find("odm:Description/odm:TranslatedText", self.ns)
        if desc is not None and desc.text and desc.text.strip():
            return desc.text.strip()

        if "def" in self.ns:
            label = node.attrib.get(f"{{{self.ns['def']}}}Label")
            if label and label.strip():
                return label.strip()

        return None

    # ---------------------------------------------------------------------
    # ✅ NEW: Dataset label extraction
    # ---------------------------------------------------------------------

    def get_dataset_label(self, domain: str) -> str:
        """Extract dataset label from ItemGroupDef Description."""

        if self.root is None:
            raise RuntimeError("Define-XML not parsed. Call parse() first.")

        dom = domain.upper()
        domain_node = self.get_domain(dom)

        label = self._get_label(domain_node)

        if label:
            logger.info("[%s] Dataset label extracted: %s", dom, label)
            return label

        logger.warning("[%s] Dataset label missing; using fallback", dom)
        return dom

    # ---------------------------------------------------------------------
    # DataType Mapping
    # ---------------------------------------------------------------------

    def _map_data_type(self, odm_type: Optional[str]) -> str:
        """Map ODM datatype to Dataset-JSON datatype."""
        if not odm_type:
            return "string"

        t = odm_type.lower()

        if t in ("text", "string"):
            return "string"
        if t in ("date", "datetime", "time"):
            return t  # Dataset-JSON v1.1 types, values stay ISO 8601 strings
        if t == "integer":
            return "integer"
        if t in ("float", "double", "decimal"):
            return "double"
        if t == "boolean":
            return "boolean"

        return "string"

    # ---------------------------------------------------------------------
    # Variable extraction
    # ---------------------------------------------------------------------

    def get_dataset_json_columns(self, domain: str) -> List[Dict]:
        """Extract Dataset-JSON column structures."""

        if self.root is None:
            raise RuntimeError("Define-XML not parsed. Call parse() first.")

        dom = domain.upper()
        logger.info("[%s] Extracting column metadata from Define-XML", dom)

        domain_node = self.get_domain(dom)
        columns: List[Dict] = []
        domain_keys = self._get_domain_keys(domain_node)

        for itemref in domain_node.findall(".//odm:ItemRef", self.ns):

            item_oid = itemref.attrib.get("ItemOID")
            if not item_oid:
                continue

            itemdef = self.root.find(
                f".//odm:ItemDef[@OID='{item_oid}']",
                self.ns
            )

            if itemdef is None:
                logger.warning("[%s] Missing ItemDef: %s", dom, item_oid)
                continue

            name = itemdef.attrib.get("Name")
            odm_type = itemdef.attrib.get("DataType")

            label = self._get_label(itemdef) or name

            length = itemdef.attrib.get("Length")
            key_seq = itemref.attrib.get("KeySequence")
            if not key_seq and name and name.upper() in domain_keys:
                key_seq = str(domain_keys.index(name.upper()) + 1)

            data_type = self._map_data_type(odm_type)
            column: Dict[str, Any] = {
                "itemOID": item_oid,
                "name": name,
                "label": label,
                "dataType": data_type,
            }

            # Dataset-JSON carries length for character variables only
            if length and data_type == "string":
                try:
                    column["length"] = int(length)
                except ValueError:
                    logger.warning("[%s] Invalid length for %s", dom, name)

            if key_seq:
                try:
                    column["keySequence"] = int(key_seq)
                except ValueError:
                    logger.warning("[%s] Invalid keySequence for %s", dom, name)

            columns.append(column)

        logger.info("[%s] Extracted %d columns", dom, len(columns))
        return columns

    # ---------------------------------------------------------------------
    # Minimal dataset-json metadata
    # ---------------------------------------------------------------------

    def get_dataset_json(self, domain: str, num_records: int = 0) -> Dict:
        """Return Dataset-JSON metadata (no rows)."""

        dom = domain.upper()

        return {
            "datasetJSONVersion": "1.1.0",
            "name": dom,
            "label": self.get_dataset_label(dom),  # ✅ UPDATED
            "records": int(num_records),
            "columns": self.get_dataset_json_columns(dom),
        }