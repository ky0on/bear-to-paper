import io
import logging
import os
import re
from uuid import uuid4
from typing import Dict, List, Text
from urllib.parse import quote

from dropbox.dropbox import Dropbox
from dropbox.sharing import SharedLinkMetadata
from dropbox.paper import ImportFormat

from reader import Reader


logger = logging.getLogger(__name__)


class Migrator(object):
    def __init__(
        self,
        documents: List[Text],
        access_token: Text,
        upload_folder: Text,
    ) -> None:
        self._paths = [
            os.path.realpath(
                os.path.expanduser(
                    document
                )
            ) for document in documents
        ]
        self._dropbox = Dropbox(access_token)
        self._upload_folder = upload_folder

    @property
    def dropbox(self):
        return self._dropbox

    def _upload_assets(
        self,
        asset_map: Dict[Text, Text],
        document_name: Text,
    ) -> Dict[Text, SharedLinkMetadata]:
        uploaded_assets: Dict[Text, SharedLinkMetadata] = {}

        for asset_key, asset_path in asset_map.items():

            ext = os.path.splitext(asset_key)[-1]
            asset_key_uuid = str(uuid4()) + ext

            logger.info("Uploading %s", asset_key_uuid)
            dropbox_path = '/' + '/'.join([
                self._upload_folder,
                # document_name,
                asset_key_uuid,
            ])

            with io.open(asset_path, 'rb') as inf:
                self.dropbox.files_upload(
                    inf.read(),
                    dropbox_path,
                    mute=True,
                )
                sharing_meta = (
                    self.dropbox.sharing_create_shared_link_with_settings(
                        dropbox_path,
                    )
                )
                logger.debug("Asset available at URL %s", sharing_meta.url)

                # asset_key_fullpath = os.path.join(document_name, asset_key)
                uploaded_assets[asset_key] = sharing_meta

        return uploaded_assets

    def _convert_markdown(
        self,
        bear_markdown: Text,
        bear_name: Text,
        uploaded_asset_map: Dict[Text, SharedLinkMetadata]
    ) -> Text:
        # First, rewrite tags that happen to have slashes:
        converted_markdown = re.sub(r'#(\w+)\/(\w+)', r'#\1_\2', bear_markdown)

        for asset_key, asset_meta in uploaded_asset_map.items():

            # Convert hyperlinks
            befores = [f'{bear_name}/{asset_key}', asset_key]
            for before in befores:
                before = quote(before, safe='/(),')
                after = asset_meta.url
                # print(f'Replacing hyperlink: {before} ---> {after}')
                converted_markdown = converted_markdown.replace(before, after)

            # Convert images
            befores = [quote(f'{bear_name}/{asset_key}')]
            for before in befores:
                before = quote(before, safe='/(),')
                after = asset_meta.url
                # print(f'Replacing image: {before} ---> {after}')
                converted_markdown = converted_markdown.replace(before, after)

        return converted_markdown

    def migrate(self) -> None:
        for path in self._paths:
            logger.info("Migrating %s", path)

            reader = Reader(path)
            bear_markdown = reader.get_markdown()
            bear_assets = reader.get_asset_map()

            # Upload assets
            uploaded_asset_map = self._upload_assets(
                bear_assets,
                reader.get_name(),
            )

            # Transform markdown
            transformed_markdown = self._convert_markdown(
                bear_markdown,
                reader.get_name(),
                uploaded_asset_map,
            )

            local_md_path = os.path.join('/tmp', os.path.basename(path))
            with open(local_md_path, 'w') as fp:
                fp.write(transformed_markdown)
            print('Saved as', local_md_path)

            # Create paper
            self.dropbox.paper_docs_create(
                transformed_markdown.encode('utf-8'),
                import_format=ImportFormat.markdown,
            )
            logger.debug("Successfully migrated %s.", path)
