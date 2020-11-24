// addtocalendar script:
if (!window.addtocalendar || typeof window.addtocalendar.start !== 'function') {
    if (typeof window.ifaddtocalendar === 'undefined') {
        window.ifaddtocalendar = 1;
        const d = document, s = d.createElement('script'), g = 'getElementsByTagName';
        s.type = 'text/javascript';
        s.charset = 'UTF-8';
        s.async = true;
        s.src = ('https:' === window.location.protocol ? 'https' : 'http') + '://addtocalendar.com/atc/1.5/atc.min.js';
        const h = d[g]('body')[0];
        h.appendChild(s);
    }
}

const AddToCalendar = function () {
    let $btn,
        $self,
        $dropdown,
        dropdownSelector = '.atcb-list';

    const init = function (selector) {
        if (typeof selector === 'undefined') {
            selector = '.atcb-link';
        }

        $btn = $(selector);

        $btn.on('click', onClick);
        $btn.on('focusin focusout', onFocusChange);
    };

    const onClick = function (event) {
        event.preventDefault();
    };

    const onFocusChange = function (event) {
        if (event.type === 'focusin') {
            $self = $(this);
            $('#group-meetings').add(window).on('scroll', onScroll);

            $dropdown = $(this).siblings(dropdownSelector);
            fixDropdownPosition($self);
        } else {
            $self = null;
            $('#group-meetings').add(window).off('scroll', onScroll);
        }
    };

    const onScroll = function () {
        fixDropdownPosition();
    };

    function fixDropdownPosition() {
        const offset = $self.offset();
        $dropdown.css('left', (offset.left + $self.outerWidth() - $dropdown.outerWidth()) + 'px');
        $dropdown.css('top', (offset.top + $self.outerHeight() - $(window).scrollTop() + 2) + 'px');
    }

    return {
        init: init
    };
}();

export {AddToCalendar};
