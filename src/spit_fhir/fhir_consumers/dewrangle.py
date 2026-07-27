"""
We'll need to manage multiple ways to consume the FHIR resources once they
are extracted. These all support the same callable interface and can be
passed to the extract run in any combination.
"""

import atexit
import json
import logging
from pathlib import Path

from .resource_consumer import ResourceConsumer


class DewrangleJSON(ResourceConsumer):
    """Buffers resources and writes them to a single JSON array file suitable
    for Dewrangle to ingest.

    TODO: this only produces a local manifest file -- it does not call the
    Dewrangle API directly. See TODO.md for the plan to replace/extend this
    with a real API-backed consumer once the upload path is defined.
    """

    def __init__(self, filename, buffersize=100):
        self.filename = filename
        self.file = None
        self.buffersize = buffersize
        self.resources = []
        self._closed = False
        atexit.register(self.close)

    def _dump_buffer_to_file(self):
        start_with_comma = True
        if self.file is None:
            start_with_comma = False
            file_path = Path(self.filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file = open(self.filename, "wt")
            self.file.write("[\n")
        if self.resources:
            if start_with_comma:
                self.file.write(",\n")
            self.file.write(
                ",\n".join(json.dumps(rsc, indent=2) for rsc in self.resources)
            )
        self.resources = []

    def __call__(self, template_name, resource, payload):
        """Feed in the resources one at a time from our iteration"""
        self.resources.append(payload)

        if len(self.resources) >= self.buffersize:
            self._dump_buffer_to_file()

    def close(self):
        """Flush any buffered resources and close out the JSON array.

        Registered as an atexit safety net, but callers should call this
        explicitly once a run completes so partial output isn't left behind
        only in the crash-recovery path.
        """
        if self._closed:
            return
        self._closed = True

        if self.resources:
            self._dump_buffer_to_file()

        if self.file:
            self.file.write("\n]")
            self.file.close()
            logging.info(f"Wrote Dewrangle manifest to '{self.filename}'")
