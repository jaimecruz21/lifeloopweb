from flask import Markup, render_template
from lifeloopweb import config, webpack

CONF = config.CONF
VIDEO_EXTENSIONS = CONF.get_array('allowed.video.extensions')


def _render(self, template, **kwargs):
    context = kwargs.get('context', {})
    if hasattr(self, 'entity'):
        entity = self.entity
    else:
        entity = self.__class__.__name__.lower()
    context[entity] = self
    return Markup(render_template(
        entity + '/_render/%s.html' % template, **context))


class ImageMixin(object):
    @property
    def entity(self):
        raise NotImplementedError('No ENTITY property')

    @property
    def default_image(self):
        raise NotImplementedError('No DEFAULT_IMAGE property')

    @property
    def main_image(self):
        raise NotImplementedError('No main_image property')

    @property
    def images(self):
        raise NotImplementedError('No images property')

    def render_main_image(self, width=41, height=41, **kwargs):
        if self.main_image.image_url:
            url = self.main_image.image_url
        else:
            url = webpack.webpack.asset_url_for('images/' + self.default_image)
        context = {
            'url': url,
            'width': width,
            'height': height,
            'class': kwargs.get('class', '')
        }
        return Markup(render_template('_renders/main_image.html', **context))

    def render_media(self):
        return Markup(render_template(
            '_renders/media.html',
            video_extensions=tuple(VIDEO_EXTENSIONS),
            images=self.images,
            entity_type=self.entity))


class MeetingMixin(object):
    entity = 'meeting'

    def render_as_list_group_item(self, **kwargs):
        return _render(self, 'as_list_group_item', **kwargs)


class GroupMixin(ImageMixin):
    entity = 'group'
    default_image = 'group.org.default.png'
    # Overrides by Organization model
    images = []
    main_image = ''

    def render_as_list_group_item(self, **kwargs):
        return _render(self, 'as_list_group_item', **kwargs)

    def render_as_alternative_list_group_item(self, **kwargs):
        return _render(self, 'as_list_group_alternative_item', **kwargs)

    def render_as_card(self, **kwargs):
        return _render(self, 'as_card', **kwargs)


class GroupDocumentMixin(object):
    entity = 'document'

    def render_as_list_group_item(self, **kwargs):
        return _render(self, 'as_list_group_item', **kwargs)


class OrganizationMixin(ImageMixin):
    entity = 'organization'
    default_image = 'group.org.default.png'
    # Overrides by Organization model
    images = []
    main_image = ''

    def render_as_list_group_item(self, **kwargs):
        return _render(self, 'as_list_group_item', **kwargs)


class UserMixin(ImageMixin):
    entity = 'user'
    default_image = 'user.default.png'
    # Overrides by User model
    images = []
    main_image = ''
