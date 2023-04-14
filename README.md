SimplyBook bookings importer
============================
To run a script or standalone windows executable, you need to have file `settings.toml` present in the same directory. This file should look like this


```toml
[Account]
domain   = "regtestig.secure.simplybook.it"
user     = "***@***.**"
password = "***"

[Files]
import_csv          = "bookings.csv"
failed_bookings_log = "failed.log"
debug_log           = "debug.log"
```

`import_csv` - defines path to csv improt file with bookings

`failed_bookings_log` - defines path to file, where all failed booking imports are logged

`debug_log` - defines path to log file, where everything is logged


Import CSV file
===============
The csv file is expected to be in following format to do the import successfully

```csv
service,provider,name,email,phone,start
Teaching service,Provider 2,John Focus,johnfocus@notando.is,3548989951,2023-04-28 09:00:00
audit services,Provider 2,Mary Focus,maryfocus@notando.is,3548989950,2023-04-25 10:00:00
Teaching service,Provider 1,Jane Anne,janeanne@notando.is,3548989700,2023-04-26 10:00:00
Teaching service,Provider 2,Alex Fulham,alexfulham@notando.is,3548989778,2023-04-27 09:00:00
```

`service` - is defined with name, lookup to `domain` is done to find service id, if no such a service is found, the csv row is skipped and logged as error

`provider` - is defined with name, lookup to `domain` is done to find provider id, if no such a provider is found, the csv row is skipped and logged as error

`name,email,phone` - are client details, if not such a client is found by `email`, it gets created automatically to store `client_id` internally

`start` - start datetime of an appointment, always should be in this format YYYY-MM-DD HH:MM:SS


How to run
==========
If you have windows executable, just doubleclick the icon, and watch out the logs.

If you want to run this as python script, you have to install packages from `requirements.txt` file by running this command `python -m pip install -r requirements.txt`. Once the packages are installed,
you simply run `python simplybook_importer.py`.

> Remember to always have `settings.toml` file present in working directory of script or windows executable and all settings correctly filled in
