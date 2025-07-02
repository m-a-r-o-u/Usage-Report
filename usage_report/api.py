"""API wrapper for LRZ SIM API."""
from __future__ import annotations

import json
import netrc
import base64
from pathlib import Path
from typing import Any

import logging
from urllib import request, error

logger = logging.getLogger(__name__)


class SimAPIError(Exception):
    """Custom exception for API errors."""


class SimAPI:
    """Wrapper around the LRZ SIM API."""

    BASE_URL = "https://simapi.sim.lrz.de/user/"

    def __init__(self, netrc_file: str | Path | None = None) -> None:
        self.netrc_file = Path(netrc_file) if netrc_file else Path.home() / ".netrc"
        logger.debug("Using netrc file %s", self.netrc_file)

    def _get_auth(self) -> tuple[str, str]:
        try:
            auths = netrc.netrc(str(self.netrc_file))
            login, _, password = auths.authenticators("simapi.sim.lrz.de")
            if not (login and password):
                raise SimAPIError("Incomplete credentials in netrc file")
            return login, password
        except (FileNotFoundError, netrc.NetrcParseError) as err:
            raise SimAPIError(f"Failed to read netrc file: {err}") from err

    def fetch_user(self, user_id: str) -> dict[str, Any]:
        """Fetch user information for *user_id*.

        Parameters
        ----------
        user_id:
            The LRZ user identifier to query.
        """
        login, password = self._get_auth()
        url = self.BASE_URL + user_id
        headers = {"Accept": "application/json"}
        credentials = f"{login}:{password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(credentials).decode()
        logger.debug("Fetching user %s from %s", user_id, url)
        req = request.Request(url, headers=headers)
        try:
            with request.urlopen(req) as resp:
                body = resp.read().decode()
                logger.debug("SIM API responded with status %s", resp.status)
                if resp.status != 200:
                    logger.debug("Response body: %s", body)
                    raise SimAPIError(
                        f"API request failed with status {resp.status}: {body}"
                    )
        except error.URLError as err:
            logger.error("Failed to contact SIM API: %s", err)
            raise SimAPIError(f"Failed to contact API: {err}") from err
        try:
            return json.loads(body)
        except json.JSONDecodeError as err:
            raise SimAPIError("Failed to decode JSON response") from err
