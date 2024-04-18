-- This migrates the old database to support pretendo. Don't forget to backup the database first.

CREATE TABLE pretendo_friends(
  friendCode text NOT NULL UNIQUE,
  online boolean NOT NULL,
  titleID text NOT NULL,
  updID text NOT NULL,
  lastAccessed bigint NOT NULL,
  accountCreation bigint NOT NULL,
  username text,
  message text,
  mii text,
  joinable boolean,
  gameDescription text,
  lastOnline bigint NOT NULL,
  jeuFavori bigint NOT NULL
);

ALTER TABLE discordFriends
ADD network tinyint; 
UPDATE discordFriends set network=0;

ALTER TABLE config
ADD network tinyint; 
UPDATE config set network=0; -- This shouldn't be needed, but safe than sorry right?

ALTER TABLE friends
RENAME TO nintendo_friends;
