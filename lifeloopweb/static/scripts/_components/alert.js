const Alert = function () {
    let $self;
    let timeout;

    const init = function (selector) {
        if (typeof selector === 'undefined') {
            selector = '#messages';
        }
        $self = $(selector);
        timeout = $self.data('successTimeout');

        setTimeout(onTimeout, timeout * 1000);
    };

    const onTimeout = function () {
        $('.alert-success').alert('close');
    };

    const create = function (message, alertType) {
        const $this = createNode();
        $this.append(message);
        $this.addClass('alert-' + alertType);

        if (alertType === 'success') {
            setTimeout(onTimeout, timeout * 1000);
        }

        $self.html($this);
    };

    const createNode = function () {
        return $('<div />', {
            'class': 'alert fade show',
            'role': 'alert'
        }).append($('<button />', {
            'type': 'button',
            'class': 'close',
            'data-dismiss': 'alert',
            'aria-label': 'Close'
        }).append($('<span />', {
            'aria-hidden': 'true',
            'html': '&times;'
        })));
    };

    return {
        init: init,
        create: create
    }
}();

export {Alert};
