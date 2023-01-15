# TERMS.md

*By using this program/app, you consent to not only knowing the contents, terms, and conditions of this document, but to agreeing to them without legally attacking me. To end your service for this app, please see [article 3](#article3).*

*These terms are subject to change without notice.*

<h3 id = 'intro'>A Brief Overview</h3>

Due to the nature of this app, it constantly scrapes the bot's friend list and saves it to a cloud database. This can mean **the user's privacy rights may appear violated during the usage of this app.** However, I am here to say that, not only is this not the case, but there are also safety measures internally placed within the app to ensure the user is never forced to give out information they do not wish to. If you'd like to immediately see those measures, please [skip to article 2](#article2). To put it simply, since the user's data is constantly being grabbed and stored, I have implemented methods to skip *some* of those steps of the procedure.

#### Scraping Objects
*Data types are based off of the SQL language (specifically, SQLite3)*

| Object | Data Type |
| --- | --- |
| `friendCode` | `text` |
| `online` | `boolean` |
| `titleID` | `text` |
| `updID` | `text` |
| `username` | `text` |
| `message` | `text` |
| `mii` | `text` |
| `joinable` | `boolean` |
| `gameDescription` | `text` |

The above objects are scraped and stored by the friend bot.

<h3 id = 'article2'>How Do I Opt-Out?</h3>

If you'd like to stop the bot's scraping of your 3DS friend account, simply remove it from your friendlist. This will not only end it from being able to receive your information, it will also *remove all of your user's information from the bot's database[\*](#article3)*. However, this will also disable its ability to scrape your user presence data, which means that it can no longer provide you a Discord status. The solution to this is simple. If the user chooses to do so, they can terminate their account information by ending their friend status message with a ` ` (space) character, and it will not be stored henceforth for so long as the status message ends with that character. Keep in mind that this does not mean information is not scraped, simply not stored -- and friend presence information (`online`, `titleID`, `updID`, `joinable`, `gameDescription`) as well as the user's friend code (`friendCode`) are still stored so that the user can still use the presence features of the app.

| Status Message | Will Bot Store Data? |
| --- | --- |
| `Hey, all!` | `True` |
|  | `True` |
| ` Hi` | `True` |
| `Hi ` | `False` |
| ` ` | `False` |

<h3 id = 'article3'>Deleting From Friend List</h3>

When deleting the bot's account from your friend list, it will no longer be able to receive data from your 3DS, including (but not limited to) the aforementioned scraping objects. It may take up to approximately ten minutes before the data is deleted from the server due to 'user cycling', in which the bot cycles through all users.
