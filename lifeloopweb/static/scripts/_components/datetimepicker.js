const DateTimePicker = function () {
    let $self;

    const init = function (selector, config_obj) {
        if (typeof selector === 'undefined') {
            selector = '.datetimepicker';
        }

        $self = $(selector);

        if ($self.length) {
            for (let key in config_obj) {
                if (config_obj.hasOwnProperty(key)) {
                    this.config[key] = config_obj[key];
                }
            }

            $self.on('focus', onFocus);
            rome(document.querySelector(selector), this.config);
        }
    };

    const onFocus = function () {
        $(this).blur();
    };

    return function () {
        this.config = {
            appendTo: 'parent',
            timeFormat: 'hh:mm A'
        };
        this.init = init;
    }
}();

export {DateTimePicker};
