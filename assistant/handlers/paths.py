import os
import re

from assistant import events, memory, pins
from assistant.registry import command, confirmable
from assistant.reply import Reply, api_button, button, copy_button
from assistant.shared import log_file_search, voice
from assistant.tools import reveal_in_explorer

_LEGACY_OPEN = ("file ", "folder ", "website ", "project ", "app ")

