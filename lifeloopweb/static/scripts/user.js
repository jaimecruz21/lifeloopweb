import {CloudinaryMedia, MediaModal} from './_components/cloudinary-media';
import {Confirm} from './_components/confirm';
import {PasswordToggler} from './_components/password-toggler';
import {PasswordValidator} from './_components/password-validator';
import {PhoneMask} from './_components/phone-mask';
import {Timezone} from './_components/timezone';

CloudinaryMedia.init();
Confirm.init();

MediaModal.init();
PasswordToggler.init();
$(document).ready(PasswordValidator.init);
PhoneMask.init();
Timezone.init($('#tz_default').val());
