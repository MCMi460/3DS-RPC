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
| `jeuFavori`\* | `bigint` |

The above objects are scraped and stored by the friend bot.  
\*`jeuFavori` is the user's favorite game

<h3 id = 'article2'>How Do I Opt-Out?</h3>

If you'd like to stop the bot's scraping of your 3DS friend account, simply remove it from your friendlist. This will not only end it from being able to receive your information, it will also *remove all of your user's information from the bot's database[\*](#article3)*. However, this will also disable its ability to scrape your user presence data, which means that it can no longer provide you a Discord status. The solution to this is simple. If the user chooses to do so, they can terminate their account information by ending their friend status message with a ` ` (space) character, and it will not be stored henceforth for so long as the status message ends with that character. Keep in mind that this does not mean information is not scraped, simply not stored -- and friend presence information (`online`, `titleID`, `updID`, `joinable`, `gameDescription`) as well as the user's friend code (`friendCode`) are still stored so that the user can still use the presence features of the app. This follows the [information cycle](#article4), so please be mindful that a register request will have to be made in order for the backend to make the changes necessary.

| Status Message | Will Bot Store Data? |
| --- | --- |
| `Hey, all!` | `True` |
|  | `True` |
| ` Hi` | `True` |
| `Hi ` | `False` |
| ` ` | `False` |

<h3 id = 'article3'>Deleting From Friend List</h3>

When deleting the bot's account from your friend list, it will no longer be able to receive data from your 3DS, including (but not limited to) the aforementioned scraping objects. It may take up to approximately ten minutes before the data is deleted from the server due to ['user cycling'](#article4), in which the bot cycles through all users.

<h3 id = 'article4'>Cycling</h3>

User cycling is broken down into two parts, both of which are updated at different speeds. The below will describe both of them as they are currently in the code (as of the commit writing this).

- Presence cycling
  - This is updated approximately every couple minutes or so. This is what reloads the display of a user's status.
  - It *can* see if a user has removed the bot from their friendlist, meaning that it will delete the user's account information after this cycle.
- Information cycling
  - This only occurs for ~5 minutes after every register. Registers will occur whenever:
    * The user registers at the website's register page. *(Does not have to be the first time)*
    * The Desktop app is opened.
  - This is what is required/necessary in order to [opt-out](#article2) of the storing your account's information. If you choose to opt-out, please make sure to then send a register request afterwards so that your information is deleted from the database within the next presence cycle.
