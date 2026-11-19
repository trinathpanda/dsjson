from dsjson.metadata.define_xml import DefineXMLParser
import os
import json


def debug_file(define_path: str):
    print("✅ Checking file existence:", os.path.exists(define_path))
    print("✅ File absolute path:", os.path.abspath(define_path))

    with open(define_path, "r", encoding="utf-8") as f:
        print("\n✅ File preview:")
        print(f.read(150))


def main():
    # Step 1: File path
    define_path = "demo/input/define.xml"

    debug_file(define_path)

    # Step 2: Initialize parser
    parser = DefineXMLParser(define_path)

    # Step 3: Parse
    parser.parse()

    # Step 4: Domains
    domains = parser.get_domains()
    print("\n✅ Domains found:")
    print(domains)

    if not domains:
        print("❌ No domains found")
        return

    # Step 5: Choose domain
    domain = "DM"

    if domain not in domains:
        print(f"❌ {domain} not found")
        return

    # Step 6: Get Dataset-JSON ✅
    dataset_json = parser.get_dataset_json(domain, num_records=100)

    print(f"\n✅ Dataset-JSON Output for {domain}:\n")

    # Pretty print JSON
    print(json.dumps(dataset_json, indent=4))


if __name__ == "__main__":
    main()