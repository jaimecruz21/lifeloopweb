let Navbar = function () {
    let className,
        $self,
        $notifications,
        $messages;

    let init = function () {
        $self = $('#navbar');
        $messages = $('#messages');

        $notifications = $('#collapseNotifications');

        let $collapse = $self.find('.navbar-collapse');
        className = $self.attr('class');

        $(window).on('scroll', onScroll);
        $(window).on('resize', onResize);
        $collapse.on('show.bs.collapse hide.bs.collapse', onCollapseToggle);
        $collapse.on('hidden.bs.collapse', onScroll);
        $notifications.on('show.bs.collapse', onShowNotifications);

        $(window).scroll();
        $(window).resize();
    };

    let onShowNotifications = function () {
        $('#navbarSupportedContent').collapse('hide');
    };

    let NavbarAbsolute = function () {
        $self.attr('class', 'navbar navbar-expand-lg text-center fixed-top navbar-dark bg-info');
        $messages.addClass('fixed-top');
    };

    let onCollapseToggle = function () {
        if ($(this).hasClass('show')) {

        } else {
            $notifications.collapse('hide');
            NavbarAbsolute();
        }
    };

    let onScroll = function () {
        if ($self.outerHeight() - $(window).scrollTop() < -200) {
            NavbarAbsolute();
        } else {
            if (!$self.find('.navbar-collapse.show').length) {
                $self.attr('class', className);
                $messages.removeClass('fixed-top');
                onResize();
            }
        }
    };

    let onResize = function () {
        if ($(window).width() < 992) {
            $('body').addClass('mobile');
        } else {
            $('body').removeClass('mobile');
        }
    };

    return {
        init: init
    };
}();

export {Navbar};
