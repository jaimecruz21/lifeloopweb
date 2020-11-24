import {AddToCalendar} from './_components/add-to-calendar';
import {Confirm} from './_components/confirm';
import {DateTimePicker} from './_components/datetimepicker';
import {MediaModal} from './_components/cloudinary-media';
import {MeetingModal} from './_components/meeting-modal';
import {onApiLoad} from './_components/google-docs-picker';
import {Disqus} from "./_components/disqus";

let $startDateTimeField = new DateTimePicker;
let $repeatEndField = new DateTimePicker;

$startDateTimeField.init('#start_datetime', {
    inputFormat: 'MM/DD/YYYY hh:mm A',
    timeInterval: 15 * 60,
    autoClose: false
});

$repeatEndField.init('#repeat_end_date', {
    inputFormat: 'MM/DD/YYYY',
    time: false
});

AddToCalendar.init();
Confirm.init();
Disqus.init();
MediaModal.init();
MeetingModal.init();
