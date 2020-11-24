import {PasswordValidator} from './_components/password-validator';
import {Timezone} from './_components/timezone';
import {PhoneMask} from './_components/phone-mask';

$(document).ready(PasswordValidator.init);
Timezone.init();
PhoneMask.init();
