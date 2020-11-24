const MeetingModal = function () {
    let $timezone,
        $startDateField,
        $repeatEndField,
        $repeatEndWrapper,
        $typeField,
        $createBtn,
        $editBtn;

    const init = function () {
        $createBtn = $('#btnAddMeeting');
        $editBtn = $('.meeting-edit');

        $startDateField = $('#start_datetime');
        $repeatEndField = $('#repeat_end_date');
        $repeatEndWrapper = $repeatEndField.closest('.form-group');
        $repeatEndWrapper.hide();

        $typeField = $('#meeting_type');
        $timezone = $('#timezone');

        $typeField.on('change', onTypeChange);
        $createBtn.on('click', onClickCreate);
        $editBtn.on('click', onClickEdit);

        if ($timezone.length) {
            const current_tz = moment.tz.guess();
            const current_offset = moment.tz(current_tz).format('Z');
            $timezone.get(0).innerHTML = current_tz + ' (' + current_offset + ')';
        }
    };

    const onClickCreate = function () {
        $typeField.val(2);
        $repeatEndField.val('');
        $repeatEndWrapper.hide();

        $('#topic').val('');
        $startDateField.val('');
        setStartDateTime();
    };

    const onClickEdit = function () {
        const $this = $(this);
        const groupId = $this.data('groupid');
        const meetingId = $this.data('meetingid');
        const meetingTime = $this.data('meetingtime');
        const topic = $this.data('topic');
        const duration = $this.data('duration');
        const repeatType = $this.data('repeattype');

        $('#groupMeetingForm').attr('action', '/groups/' + groupId + '/meeting/' + meetingId);
        $('#btnGroupMeeting').attr('value', 'Update');
        $('#meeting_id').val(meetingId);
        $('#duration').val(duration);
        $('#topic').val(topic);

        switch (repeatType) {
            case 3:
                $typeField.val(3);
                $repeatEndWrapper.fadeIn();
                const repeatDate = $this.data('repeatdate');
                if (repeatDate) {
                    $repeatEndField.val(moment(repeatDate).format('MM/DD/YYYY'));
                }
                break;
            default:
                $typeField.val(2);
                $repeatEndWrapper.fadeOut();
                $repeatEndField.val('');
        }

        setStartDateTime(meetingTime);
    };

    const onTypeChange = function () {
        const meeting_type = $typeField.val();

        switch (meeting_type) {
            case '3':
                $repeatEndWrapper.fadeIn();
                break;
            default:
                $repeatEndWrapper.fadeOut();
                $repeatEndField.val('');
        }
    };

    function setStartDateTime(dt) {
        let utcTime;

        if (typeof dt === 'undefined') {
            const start = moment(new Date());
            const remainder = (15 - start.minute()) % 15;
            utcTime = moment(start).add(remainder, 'minutes').format('MM/DD/YYYY hh:mm A');
        } else {
            utcTime = moment.utc(dt);
        }

        const localTime = moment(utcTime).local();
        $startDateField.val(localTime.format('MM/DD/YYYY hh:mm A'));
    }

    return {
        init: init
    }
}();

export {MeetingModal};
