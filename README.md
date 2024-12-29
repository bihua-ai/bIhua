
```
# How to Use Bihua

### 1. Create Directories

- Create the `data` directory.
- Create the `data/configs` directory. Put .env anf log.conf 

### 2. Set Configuration Path

From the terminal, run:

```bash
export BIHUA_CONFIG_DIR="/opt/bihua/data/configs"
```

### 3. Install Bihua

Install Bihua using pip:

```bash
pip install bihua
```

### 4. Write Your Own `team1.py`, usse your own name. `team1.py` is an example.

Add the following code to your `team1.py` file:

```python
import sys
sys.path.append('/opt/bihua/bihua') # check later, do we have to put it here.

from bihua import BihuaAgentService, BihuaEvent
import bihua
```

### 5. Write Your Own Event Handler

Define your event handler. For example:

```python
on_message_received_bot_001:
```

- Do not change `"on_message_received"`.
- `"bot_001"` is the name of the agent (e.g., `@bot_001:servername`).

### How to Run

Run the following command to start the service:

```bash
python3 team1.py -config_path /opt/bihua/data/config -group_alias "#bot_org3:messenger.b1.shuwantech.com" -group_topic "Team One" -agent_dir_path "/opt/bihua_client/agents"
```

### In `team1.py`:

Define the default values for the group alias, group topic, and agent directory path:

```python
default_group_alias = "#bot_org3:messenger.b1.shuwantech.com"
default_group_topic = "Bot Team 1"
default_agent_dir_path = "/opt/bihua_client/agents"
```

### 6. Agent Directory

The agents can be in any directory. You just need to specify the paths in `/opt/bihua/bihua/team1.py`:

```bash
/opt/bihua/bihua/agents
```
```

You can now copy this directly into your `README.md` file.