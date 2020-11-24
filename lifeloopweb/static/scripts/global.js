import 'bootstrap';
import 'jquery.redirect';
import './_components/zendesk';
import './_components/google-analytics';
import {Alert} from './_components/alert';
import {Expand} from './_components/expand';
import {GroupModal} from './_components/group-modal';
import {Navbar} from './_components/navbar';
import {NotificationInfo} from './_components/notification-info';
import {ScrollTo} from './_components/scroll-to';
import {Search} from './_components/search';
import {Subscription} from './_components/subscription';
import {introJs} from 'intro.js';

$("#show-hints").click(function(){
	introJs().addHints()
})

if ($(window).width() > 991) {
    $('[data-toggle="tooltip"]').tooltip({trigger: 'hover'});
}

const onShowBsModal = function () {
    const zIndex = 1040 + (10 * $('.modal:visible').length);
    $(this).css('z-index', zIndex);

    const onSetTimeout = function () {
        $('.modal-backdrop').not('.modal-stack').css('z-index', zIndex - 1).addClass('modal-stack');
    };

    setTimeout(onSetTimeout, 0);
};

$(document).on('show.bs.modal', '.modal', onShowBsModal);

Alert.init();
Expand.init();
GroupModal.init();
Navbar.init();
NotificationInfo.init();
Search.init();
ScrollTo.init();

if ($('body').data('featureSubscriptionOn')) {
    Subscription.init();
}
