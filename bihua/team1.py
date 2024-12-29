import argparse
import asyncio
# from bihua.configuration_manager import initialize_config_manager, 
import configuration_manager
from agent_service import BihuaAgentService

# Default values
default_group_alias = "#bot_org3:messenger.b1.shuwantech.com"
default_group_topic = "Bot Team 1"
default_agent_dir_path = "/opt/bihua_cient/agents"

# Function to run the agent group
async def bihua_agent_group_runner(group_alias, group_topic, agent_dir_path, bihua_agent_service_config_location):

    # config_loader = config_manager.get_config_loader()  # Now we can directly use config_manager

    agent_service = BihuaAgentService(bihua_agent_service_config_location)  # Create the app service
    await agent_service.agent_group_runner(group_alias, group_topic, agent_dir_path)

# Entry point
if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Run the Bihua Agent Group runner")
    
    # Add arguments
    parser.add_argument('-config_path', type=str, default='/opt/bihua/data/config', 
                        help="Path to the Bihua agent service config directory (default: '/opt/bihua/data/config')")
    parser.add_argument('-group_alias', type=str, default=default_group_alias, 
                        help="Alias of the agent group (default: '#bot_org3:messenger.b1.shuwantech.com')")
    parser.add_argument('-group_topic', type=str, default=default_group_topic, 
                        help="Topic of the agent group (default: 'Bot Team 1')")
    parser.add_argument('-agent_dir_path', type=str, default=default_agent_dir_path, 
                        help="Path to the directory where agents' pytho files are stored (default: '/opt/bihua_cient/agents')")
    
    # Parse arguments
    args = parser.parse_args()

    # Initialize the config_manager with the provided config path
    # configuration_manager.initialize_config_manager(args.config_path)
    
    # Run the agent group runner with the provided or default config path
    # python3 team1.py -config_path /opt/bihua/data/config -group_alias "#bot_org3:messenger.b1.shuwantech.com" -group_topic "Team One" -agent_dir_path "/opt/bihua_cient/agents"
    asyncio.run(bihua_agent_group_runner(args.group_alias, args.group_topic, args.agent_dir_path, args.config_path))
