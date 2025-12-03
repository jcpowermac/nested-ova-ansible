#!/usr/bin/env python3
"""
Ansible filter plugin for structured logging during deployment
"""

import json
from datetime import datetime


class FilterModule:
    """Ansible filter plugin for deployment logging"""

    def filters(self):
        return {
            'deployment_log': self.deployment_log,
            'format_deployment_message': self.format_deployment_message,
            'json_log': self.json_log
        }

    def deployment_log(self, message, level='INFO', context=None):
        """
        Create a structured log entry in JSON format

        Args:
            message: Log message string
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            context: Optional dictionary with additional context

        Returns:
            JSON-formatted log string
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level.upper(),
            'message': str(message),
            'context': context or {}
        }
        return json.dumps(log_entry)

    def format_deployment_message(self, message, **kwargs):
        """
        Format a deployment message with context

        Args:
            message: Message template
            **kwargs: Context variables to include in the message

        Returns:
            Formatted message string
        """
        if not kwargs:
            return message

        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            # Fallback if formatting fails
            context_str = ', '.join(f"{k}={v}" for k, v in kwargs.items())
            return f"{message} [{context_str}]"

    def json_log(self, data):
        """
        Convert data to pretty-printed JSON for logging

        Args:
            data: Any JSON-serializable data

        Returns:
            Pretty-printed JSON string
        """
        try:
            return json.dumps(data, indent=2, sort_keys=True)
        except (TypeError, ValueError) as e:
            return f"Error serializing to JSON: {str(e)}"
