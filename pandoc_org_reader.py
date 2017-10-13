import logging
import os
import re
import subprocess
from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

log = logging.getLogger(__name__)

METADATA_PATTERN = re.compile(r'^#\+(?P<name>.*?):(?P<value>.*)')

class PandocOrgReader(BaseReader):
    enabled = True
    file_extensions = ['org']

    def read(self, filename):
        log.info("Reading org file {0}...".format(filename))
        with pelican_open(filename) as fp:
            raw_content = fp
            text = list(fp.splitlines())

        metadata = {}
        for i, line in enumerate(text):
            mo = METADATA_PATTERN.match(line)
            if not mo:
                content = "\n".join(text[i:])
                break

            name = mo.group("name").lower()
            value = mo.group("value").strip()
            if name == "property":
                chunks = [x.strip() for x in value.split(" ", 1)]
                if len(chunks) == 2:
                    name = chunks[0].lower()
                    value = chunks[1]
                elif len(chunks) == 1 and chunks[0]:
                    name = chunks[0].lower()
                    value = ''
                else:
                    continue

            if name == "date":
                value = value.strip("<>").split()[0]
            elif name == "tags":
                value = [x.strip() for x in value.split(",") if x.strip()]

            metadata[name] = self.process_metadata(name, value)

        extra_args = self.settings.get('PANDOC_ORG_ARGS', [])
        extensions = self.settings.get('PANDOC_ORG_EXTENSIONS', '')
        if isinstance(extensions, list):
            extensions = ''.join(extensions)

        script_path = os.path.dirname(os.path.realpath(__file__))
        pandoc_cmd = ["pandoc", "--from=org" + extensions, "--to=html5"]
        pandoc_cmd.extend(extra_args)

        proc = subprocess.Popen(pandoc_cmd,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE)

        document = proc.communicate(content.encode('utf-8'))[0].decode('utf-8')
        status = proc.wait()
        if status:
            raise subprocess.CalledProcessError(status, pandoc_cmd)

        # generate highlighted source
        generate_source = self.settings.get('PANDOC_ORG_GENERATE_SOURCE', False)
        if generate_source:
            pygmentize_cmd = ["pygmentize", "-l", "org", "-f", "html"]

            proc = subprocess.Popen(pygmentize_cmd,
                                    stdin = subprocess.PIPE,
                                    stdout = subprocess.PIPE)

            source = proc.communicate(raw_content.encode('utf-8'))[0].decode('utf-8')
            status = proc.wait()
            if status:
                raise subprocess.CalledProcessError(status, pygmentize_cmd)

            metadata["source"] = source

        return document, metadata

def add_reader(readers):
    for ext in PandocOrgReader.file_extensions:
        readers.reader_classes[ext] = PandocOrgReader

def register():
    signals.readers_init.connect(add_reader)
