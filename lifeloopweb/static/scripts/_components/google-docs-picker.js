const $btn = $('#picker-button');
const a = $btn.data('apiKey');
const c = $btn.data('clientId');

let pickerApiLoaded = false,
    oauthToken;

function onApiLoad() {
    gapi.load('auth', {'callback': onAuthApiLoad});
    gapi.load('picker', {'callback': onPickerApiLoad});
}

$btn.on('click', onApiLoad);

function onAuthApiLoad() {
    window.gapi.auth.authorize({
        'client_id': c,
        'scope': ['https://www.googleapis.com/auth/docs'],
        'immediate': false
    }, handleAuthResult);
}

function onPickerApiLoad() {
    pickerApiLoaded = true;
    createPicker();
}

function handleAuthResult(authResult) {
    if (authResult && !authResult.error) {
        oauthToken = authResult.access_token;
        createPicker();
    }
}

// Create and render a Picker object for picking user Docs.
function createPicker() {
    if (pickerApiLoaded && oauthToken) {
        const picker = new google.picker.PickerBuilder().addView(
            google.picker.ViewId.DOCS).setOAuthToken(
                oauthToken).setDeveloperKey(
                    a).setCallback(
                        pickerCallback).build();
        picker.setVisible(true);
    }

    $('.show').hide();
}

// Callback implementation to submit form when file is selected
function pickerCallback(data) {
    let url = 'nothing',
        name;

    if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
        const doc = data[google.picker.Response.DOCUMENTS][0];
        url = doc[google.picker.Document.URL];
        name = doc[google.picker.Document.NAME];

        $('#link').val(url);
        $('#filename').val(name);
        $('#btnGroupAddGoogleDoc').click();
    }
}

export {onApiLoad};
