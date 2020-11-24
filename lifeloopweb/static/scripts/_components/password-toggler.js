const PasswordToggler = function () {
    let $self,
        $input,
        toggleArray;

    const init = function (selector) {
        if (typeof selector === 'undefined') {
            selector = '.input-toggle[data-toggle]';
        }

        $self = $(selector);
        $self.on('click', '.toggler', onClick);
    };

    const onClick = function (event) {
        toggleArray = $(this).parent().data('toggle').split('|');
        $input = $(this).siblings('.form-control');

        $(this).toggleClass('active');

        if ($input.attr('type') === toggleArray[0]) {
            $input.attr('type', toggleArray[1]);
        } else {
            $input.attr('type', toggleArray[0]);
        }

        $input.focus();
    };

    return {
        init: init
    };
}();

export {PasswordToggler};
