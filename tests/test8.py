import importlib.util, importlib


def import_handler(agent_id, agent_file_path, agent_callback_name="on_message_received"):
        """Dynamically import the handler for the agent."""

        print(f"1. Importing handler for {agent_id} from {agent_file_path}...")
        # logger.info(f"Importing handler for {agent_id} from {agent_file_path}...")
        try:
            print(f"2. Importing handler for {agent_id} from {agent_file_path}...")
            # Load the module from the given file path
            spec = importlib.util.spec_from_file_location(agent_id, agent_file_path)
            print(f"Module spec: {spec}")

            if spec is None or spec.loader is None:
                # logger.error(f"Failed to load module spec for {agent_id} from {agent_file_path}.")
                return None

            agent_module = importlib.util.module_from_spec(spec)
            print(f"Agent module: {agent_module}")

            spec.loader.exec_module(agent_module)
            

            # Construct the handler function name dynamically
            callback_function_name = f"{agent_callback_name}_{agent_id}"
            # Dynamically get the handler function from the module
            print(f"callback_function_name: {callback_function_name}")
            handler = getattr(agent_module, callback_function_name, None)
            print(f"handler: {handler}")
            if handler is None:
                # logger.error(f"Handler function '{callback_function_name}' not found in the module '{agent_id}'.")
                return None

            # logger.info(f"Handler function '{callback_function_name}' successfully loaded for {agent_id}.")
            return handler
        except Exception as e:
            # logger.error(f"Error importing handler for {agent_id}: {e}")
            print(f"Error importing handler for {agent_id}: {e}")
            return None
        
agent_id = "bot_001"
agent_file_path = "/opt/bihua_cient/agents/bot_001.py"
import_handler(agent_id, agent_file_path)