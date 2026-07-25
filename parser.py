import os
import yaml
import json

def parse_compose_files(base_dir=None):
    if base_dir is None:
        base_dir = os.getenv("BASE_DIR", "/containers")
    results = []
    
    compose_paths = []
    for root, dirs, files in os.walk(base_dir):
        rel_path = os.path.relpath(root, base_dir)
        depth = 0 if rel_path == "." else len(rel_path.split(os.sep))
        if depth > 2:
            dirs.clear()
            continue
        if "docker-compose.yaml" in files:
            compose_paths.append(os.path.join(root, "docker-compose.yaml"))
            
    for compose_path in compose_paths:
        stack_dir = os.path.dirname(compose_path)
        stack_name = os.path.relpath(stack_dir, base_dir)
        
        try:
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
                
            if not compose_data or "services" not in compose_data:
                continue
                
            for service_name, service_config in compose_data["services"].items():
                if not service_config:
                    continue
                    
                container_name = service_config.get("container_name", service_name)
                image = service_config.get("image", "unknown")
                
                # Parse ports
                ports = []
                ports_config = service_config.get("ports", [])
                if isinstance(ports_config, list):
                    for p in ports_config:
                        if isinstance(p, str):
                            ports.append(p)
                        elif isinstance(p, dict):
                            host = p.get("published", "")
                            container = p.get("target", "")
                            if host and container:
                                ports.append(f"{host}:{container}")
                elif isinstance(ports_config, dict):
                    pass
                    
                # Check network_mode: host
                network_mode = service_config.get("network_mode", "")
                if network_mode == "host":
                    ports.append("host")
                    
                # Parse networks
                networks = []
                networks_config = service_config.get("networks", [])
                if isinstance(networks_config, list):
                    networks = networks_config
                elif isinstance(networks_config, dict):
                    networks = list(networks_config.keys())
                    
                # Parse labels
                labels = {}
                labels_config = service_config.get("labels", {})
                if isinstance(labels_config, list):
                    for lbl in labels_config:
                        if "=" in lbl:
                            k, v = lbl.split("=", 1)
                            labels[k.strip()] = v.strip()
                        elif ":" in lbl:
                            k, v = lbl.split(":", 1)
                            labels[k.strip()] = v.strip()
                elif isinstance(labels_config, dict):
                    for k, v in labels_config.items():
                        labels[str(k).strip()] = str(v).strip()
                        
                # Extract Caddy settings
                caddy_public = labels.get("caddy", "-")
                caddy_lan = "-"
                tinyauth_sso = "No"
                
                for k, v in labels.items():
                    if k.startswith("caddy_") and not k.endswith(".reverse_proxy"):
                        caddy_lan = v
                    if k.startswith("caddy.import_") and v == "tinyauth":
                        tinyauth_sso = "Yes"
                    if k.startswith("caddy_") and "tinyauth" in v:
                        tinyauth_sso = "Yes"
                        
                results.append({
                    "container_name": container_name,
                    "service_name": service_name,
                    "stack": stack_name,
                    "image": image,
                    "ports": ports,
                    "networks": networks,
                    "caddy_public": caddy_public,
                    "caddy_lan": caddy_lan,
                    "tinyauth": tinyauth_sso,
                    "labels": labels
                })
        except Exception as e:
            print(f"Error parsing {compose_path}: {e}")
            
    return results

if __name__ == "__main__":
    data = parse_compose_files()
    output_path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated {output_path} with {len(data)} containers.")
