import {Alert} from './alert';

const Clipboard = function () {
    let $btn;

    const init = function () {
        $btn = $('.clipboard');

        $btn.on('click', onClick);
    };

    const onClick = function () {
        $(this).parent().parent().find('input').select();

        try {
            document.execCommand('copy');
            Alert.create('Link has been copied to your clipboard.', 'success');
        } catch (err) {
            console.warn(err);
        }
    };

    return {
        init: init
    };
}();

export {Clipboard};
