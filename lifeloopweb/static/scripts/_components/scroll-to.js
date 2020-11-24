let ScrollTo = function () {
    const $NAVBAR = $('#navbar');

    let init = function () {
        let $links = $('.ll-scroll');

        $links.on('click', onClick);
    };

    let onClick = function (event) {
        event.preventDefault();

        let $target = $($(this).attr('href'));

        $('html, body').animate({
            scrollTop: $target.offset().top - ($NAVBAR.outerHeight() * 2)
        }, 1200);
    };

    return {
        init: init
    };
}();

export {ScrollTo};
