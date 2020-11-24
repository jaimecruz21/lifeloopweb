import 'jquery-ui';
import 'jquery-ui/ui/widgets/sortable';

const OrgGroupsSortable = function () {
    const $self = $('#org-groups-sortable');

    let children;

    let settings = {
        cursor: 'move',
        handle: '.card-header',
        opacity: 0.75,
        placeholder: '',
        revert: true
    };

    const init = function () {
        settings.start = onStart;
        settings.update = onUpdate;

        $self.sortable(settings);
    };

    const onStart = function (event, ui) {
        ui.placeholder.height(ui.item.height());
    };

    const onUpdate = function () {
        children = $self.children();

        let location_array = window.location.href.split('/');
        let data = {
            org_id: location_array[location_array.length - 1],
            group_ids: Array.from(children.map(i => children[i].dataset.groupId))
        };

        $.post('/organizations/groups/sort', data, function (response) {

        }, 'json');
    };

    return {
        init: init
    };
}();

OrgGroupsSortable.init();
