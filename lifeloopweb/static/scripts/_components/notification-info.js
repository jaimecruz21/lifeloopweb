const NotificationInfo = function () {
    const $btn = $('[data-notification-info]');
    const $modal = $('#notificationInfoModal');
    let $modalBody;
    let $modalFooter;

    const init = function () {
        if ($btn.length) {
            $btn.on('click', onClick);
            $modalBody = $modal.find('.modal-body');
            $modalFooter = $modal.find('.modal-footer');
        }
    };

    const onClick = function (event) {
        event.preventDefault();

        const notificationInfoUrl = this.dataset['notificationInfo'],
              notificationBlockUrl = this.dataset['notificationBlock'];

        $modalBody.load(notificationInfoUrl, onLoad);
        $modalFooter.find('a').attr('data-action', notificationBlockUrl);
        $modalFooter.show();
    };

    const onLoad = function (responseText, textStatus) {
        if (textStatus === 'error') {
            $modalBody.html(responseText);
            $modalFooter.hide();
        }
    };

    return {
        init: init
    }
}();

export {NotificationInfo};
