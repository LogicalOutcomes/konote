"""ODK Central REST API client.

Wraps the ODK Central API for managing projects, forms, entities,
and app users. Used by the sync_odk management command.

ODK Central API docs: https://docs.getodk.org/central-api/
"""

import logging

import requests

logger = logging.getLogger(__name__)


class ODKCentralError(Exception):
    """Raised when an ODK Central API call fails."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ODKCentralClient:
    """Client for the ODK Central REST API.

    Usage:
        client = ODKCentralClient(
            base_url="https://odk.example.com",
            email="admin@example.com",
            password="secret",
        )
        projects = client.list_projects()
    """

    def __init__(self, base_url, email, password, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout
        self._session = requests.Session()
        self._token = None

    def _authenticate(self):
        """Obtain a session token from ODK Central."""
        resp = self._session.post(
            f"{self.base_url}/v1/sessions",
            json={"email": self.email, "password": self.password},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise ODKCentralError(
                f"Authentication failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        self._token = resp.json()["token"]
        self._session.headers["Authorization"] = f"Bearer {self._token}"

    def _request(self, method, path, **kwargs):
        """Make an authenticated API request, auto-authenticating if needed."""
        if not self._token:
            self._authenticate()

        kwargs.setdefault("timeout", self.timeout)
        url = f"{self.base_url}/v1{path}"
        resp = self._session.request(method, url, **kwargs)

        # Re-authenticate on 401 (token expired) and retry once
        if resp.status_code == 401:
            self._authenticate()
            resp = self._session.request(method, url, **kwargs)

        if resp.status_code >= 400:
            raise ODKCentralError(
                f"API error {resp.status_code}: {method} {path}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        return resp

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(self):
        """List all projects."""
        return self._request("GET", "/projects").json()

    def create_project(self, name):
        """Create a new project. Returns the project dict."""
        return self._request(
            "POST", "/projects", json={"name": name}
        ).json()

    def get_project(self, project_id):
        """Get a single project by ID."""
        return self._request("GET", f"/projects/{project_id}").json()

    def update_project(self, project_id, name):
        """Update a project's name."""
        return self._request(
            "PATCH", f"/projects/{project_id}", json={"name": name}
        ).json()

    # ------------------------------------------------------------------
    # Forms
    # ------------------------------------------------------------------

    def list_forms(self, project_id):
        """List all forms in a project."""
        return self._request("GET", f"/projects/{project_id}/forms").json()

    def create_form(self, project_id, xlsform_path):
        """Upload an XLSForm to create a new form definition."""
        with open(xlsform_path, "rb") as f:
            return self._request(
                "POST",
                f"/projects/{project_id}/forms",
                headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                data=f.read(),
            ).json()

    def publish_form(self, project_id, form_id):
        """Publish a draft form to make it available for data collection."""
        return self._request(
            "POST", f"/projects/{project_id}/forms/{form_id}/draft/publish"
        ).json()

    # ------------------------------------------------------------------
    # Entity Lists (Datasets)
    # ------------------------------------------------------------------

    def list_entity_lists(self, project_id):
        """List all entity lists (datasets) in a project."""
        return self._request(
            "GET", f"/projects/{project_id}/datasets"
        ).json()

    def create_entity_list(self, project_id, name, properties=None):
        """Create a new entity list with optional properties.

        Args:
            project_id: ODK Central project ID
            name: Entity list name (e.g., "Participants")
            properties: List of property dicts, e.g.,
                [{"name": "first_name"}, {"name": "last_initial"}]
        """
        payload = {"name": name}
        resp = self._request(
            "POST", f"/projects/{project_id}/datasets", json=payload
        )
        dataset = resp.json()

        # Add properties to the entity list
        if properties:
            for prop in properties:
                self._request(
                    "POST",
                    f"/projects/{project_id}/datasets/{name}/properties",
                    json={"name": prop["name"]},
                )
        return dataset

    def list_entities(self, project_id, dataset_name):
        """List all entities in a dataset."""
        return self._request(
            "GET", f"/projects/{project_id}/datasets/{dataset_name}/entities"
        ).json()

    def create_entity(self, project_id, dataset_name, label, data, uuid=None):
        """Create a single entity in a dataset.

        Args:
            project_id: ODK Central project ID
            dataset_name: Entity list name (e.g., "Participants")
            label: Display label for the entity
            data: Dict of property values (e.g., {"first_name": "Maria"})
            uuid: Optional UUID; auto-generated if not provided
        """
        payload = {"label": label, "data": data}
        if uuid:
            payload["uuid"] = uuid
        return self._request(
            "POST",
            f"/projects/{project_id}/datasets/{dataset_name}/entities",
            json=payload,
        ).json()

    def update_entity(self, project_id, dataset_name, entity_uuid, data, label=None):
        """Update an existing entity's properties."""
        # Get current version first for conflict detection
        entity = self._request(
            "GET",
            f"/projects/{project_id}/datasets/{dataset_name}/entities/{entity_uuid}",
        ).json()

        payload = {"data": data}
        if label:
            payload["label"] = label

        return self._request(
            "PATCH",
            f"/projects/{project_id}/datasets/{dataset_name}/entities/{entity_uuid}",
            params={"baseVersion": entity["currentVersion"]["version"]},
            json=payload,
        ).json()

    def delete_entity(self, project_id, dataset_name, entity_uuid):
        """Delete an entity from a dataset."""
        self._request(
            "DELETE",
            f"/projects/{project_id}/datasets/{dataset_name}/entities/{entity_uuid}",
        )

    def create_entities_sequential(self, project_id, dataset_name, entities):
        """Create multiple entities one at a time.

        ODK Central does not have a bulk create endpoint (as of 2025),
        so each entity requires a separate HTTP request. For large lists
        (500+ participants) this may take several minutes.

        Args:
            entities: List of dicts with "label" and "data" keys.
        """
        created = []
        for entity_data in entities:
            result = self.create_entity(
                project_id,
                dataset_name,
                label=entity_data["label"],
                data=entity_data["data"],
                uuid=entity_data.get("uuid"),
            )
            created.append(result)
        return created

    # ------------------------------------------------------------------
    # Submissions (OData)
    # ------------------------------------------------------------------

    def get_submissions(self, project_id, form_id, since=None):
        """Get form submissions, optionally filtered by date.

        Args:
            project_id: ODK Central project ID
            form_id: Form XML ID (e.g., "session_attendance")
            since: ISO datetime string to filter submissions after this time
        """
        params = {}
        if since:
            params["$filter"] = f"__system/submissionDate gt {since}"
        return self._request(
            "GET",
            f"/projects/{project_id}/forms/{form_id}.svc/Submissions",
            params=params,
        ).json().get("value", [])

    # ------------------------------------------------------------------
    # App Users
    # ------------------------------------------------------------------

    def list_app_users(self, project_id):
        """List all app users in a project."""
        return self._request(
            "GET", f"/projects/{project_id}/app-users"
        ).json()

    def create_app_user(self, project_id, display_name):
        """Create an app user for mobile data collection."""
        return self._request(
            "POST",
            f"/projects/{project_id}/app-users",
            json={"displayName": display_name},
        ).json()

    def assign_app_user_to_form(self, project_id, form_id, app_user_id, role_id=2):
        """Give an app user access to a specific form.

        role_id=2 is the default "Data Collector" role in ODK Central.
        """
        self._request(
            "POST",
            f"/projects/{project_id}/forms/{form_id}/assignments/{role_id}/{app_user_id}",
        )
