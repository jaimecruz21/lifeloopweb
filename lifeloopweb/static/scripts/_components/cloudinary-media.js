import './cloudinary-upload-widget';
import 'cloudinary-video-player/dist/cld-video-player.min';
import {Alert} from './alert';

const CloudinaryMedia = function () {
    let entityType;
    let entityId;
    let environment;
    let cloudinaryApiKey;
    let cloudinaryCloudName;
    let cloudinaryUploadPreset;

    const init = function () {
        entityType = $('#entity_type').val();
        entityId = $('#entity_id').val();
        environment = $('#env').val();
        cloudinaryApiKey = $('#cloudinary_api_key').val();
        cloudinaryCloudName = $('#cloudinary_cloud_name').val();
        cloudinaryUploadPreset = $('#cloudinary_upload_preset').val();

        const generateSignature = function (callback, params_to_sign) {
            $.ajax({
                url: '/images/signature',
                type: 'GET',
                dataType: 'text',
                data: params_to_sign,
                success: function (signature, textStatus, xhr) {
                    callback(signature);
                },
                error: function (xhr, status, error) {
                    Alert.create('Error uploading image. Please try again later.', 'danger');
                }
            });
        };

        $('#upload_widget_opener').cloudinary_upload_widget({
            api_key: cloudinaryApiKey,
            cloud_name: cloudinaryCloudName,
            upload_preset: cloudinaryUploadPreset,
            cropping: 'server',
            cropping_show_dimensions: true,
            multiple: false,
            theme: 'white',
            tags: [environment],
            folder: entityType + '/' + entityId + '/',
            button_class: 'btn btn-primary btn-sm d-flex',
            button_caption: '<div class="d-flex"><span class="icon icon-plus mr-2"><svg xmlns="http://www.w3.org/2000/svg" width="8px" height="8px" viewBox="0 0 8 8"><path d="M8,3.3H4.7V0H3.3v3.3H0v1.3h3.3V8h1.3V4.7H8V3.3z"></path></svg></span>Add Media</div>',
            upload_signature: generateSignature
        }, function (error, result) {
            if (error) {
                console.log(error);
            }
        });

        $(document).on('cloudinarywidgetfileuploadsuccess', onUploadSuccess);
        $(document).on('cloudinarywidgeterror', onWidgetError);
    };

    const onUploadSuccess = function (e, data) {
        const entityType = $('#entity_type').val();
        const entityId = $('#entity_id').val();

        $.redirect('/images/' + entityType + '/' + entityId, {
            url: data['secure_url'],
            public_id: data['public_id']
        });
    };

    const onWidgetError = function (e, data) {
        Alert.create("Error uploading image. Please try again later.", 'danger');
    };

    return {
        init: init
    }
}();

let $DOCUMENT = $(document);

const MediaModal = function () {
    let $self,
        media_src,
        $body,
        $target,
        $next,
        $prev,
        $remove,
        cld;

    const init = function () {
        $self = $('#galleryModal');

        if ($self.length) {
            $next = $('.gallery-next');
            $prev = $('.gallery-prev');
            $body = $self.find('.modal-body');
            $remove = $('.delete-image');

            $self.on('show.bs.modal', onShow);
            $self.on('hidden.bs.modal', onHidden);
            $prev.on('click', onPrevClick);
            $next.on('click', onNextClick);
            cloudinaryVideoPlayer();
        }
    };

    const cloudinaryVideoPlayer = function () {
        cld = cloudinary.Cloudinary.new({
            cloud_name: $('#cloudinary_cloud_name').val(),
            secure: true
        });

        init_players('.cld-video-player');
    };

    const init_players = function (selector) {
        let method = 'videoPlayers';

        if (selector.charAt(0) !== '.') {
            method = 'videoPlayer';
        }

        cld[method](selector, {
            posterOptions: {
                startOffset: 5,
                transformation: {
                    effect: ['improve']
                }
            },
            controls: true,
            sourceTypes: ['webm', 'mp4', 'mov']
        });
    };

    const onShow = function (event) {
        $target = $(event.relatedTarget);
        $DOCUMENT.on('keydown', onKeydown);
        handleMedia($target);
    };

    const onHidden = function () {
        $DOCUMENT.off('keydown', onKeydown);

        $body.empty();
    };

    const handleMedia = function ($target) {
        if ($target.length) {
            $remove.attr('data-action', '/images/' + $target.data('imageid') + '/' + $target.data('entitytype'));

            if ($target.children('video').length || $target.children('div').length) {
                showVideo($target);
            } else {
                showImage($target);
            }
        }
    };

    const showVideo = function ($target) {
        $body.html($('<video />', {
            'id': 'modal-player',
            'class': 'cld-video-player cld-video-player-skin-light cld-fluid',
            'data-cld-public-id': $target.children().data('cldPublicId')
        }));

        init_players('modal-player');
    };

    const showImage = function ($target) {
        media_src = get_gallery_image_url($target);

        $body.html($('<img />', {
            'class': 'img-fluid',
            'src': media_src
        }));
    };

    const get_gallery_image_url = function (elem) {
        if (elem.find('img').length > 0) {
            return elem.find('img').attr('src');
        } else {
            return elem.css('background-image').replace('url(', '').replace(')', '').replace(/\"/gi, '');
        }
    };

    const onPrevClick = function () {
        if ($target.parent().prev().length) {
            $target = $($target.parent().prev().children());
            handleMedia($target);
        }
    };

    const onNextClick = function () {
        if ($target.parent().next().length) {
            $target = $($target.parent().next().children());
            handleMedia($target);
        }
    };

    const onKeydown = function (event) {
        if (event.keyCode === 37) {
            onPrevClick();
        } else if (event.keyCode === 39) {
            onNextClick();
        }
    };

    return {
        init: init
    };
}();

export {CloudinaryMedia, MediaModal};
