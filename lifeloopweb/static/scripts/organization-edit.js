import {AnalyticsCollapses} from './_components/analytics-collapses';
import {Confirm} from './_components/confirm';
import {Charts} from './_components/charts';
import {CloudinaryMedia, MediaModal} from './_components/cloudinary-media';
import {Clipboard} from './_components/clipboard';
import {DateTimePicker} from './_components/datetimepicker';
import {MemberChangeStatus} from './_components/member-change-status';
import {LinkModal} from './_components/link-modal';

AnalyticsCollapses.init();
Charts.init();
CloudinaryMedia.init();
Clipboard.init();
Confirm.init();
LinkModal.init();

const foundedDate = new DateTimePicker;
foundedDate.init('#date_founded', {
    inputFormat: 'MM/DD/YYYY',
    max: new Date(),
    time: false
});

MediaModal.init();
MemberChangeStatus.init();
