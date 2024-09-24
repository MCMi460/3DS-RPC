Create Table friends(
  friendCode text NOT NULL UNIQUE,
  network tinyint NOT NULL,
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

Create Table config(
  backend_uptime text,
  network tinyint NOT NULL
);

INSERT INTO config(backend_uptime, network) VALUES (NULL, 0);
INSERT INTO config(backend_uptime, network) VALUES (NULL, 1);

Create Table discord(
  ID bigint NOT NULL UNIQUE,
  refresh text NOT NULL,
  bearer text NOT NULL,
  session text,
  token text UNIQUE,
  lastAccessed bigint NOT NULL,
  generationDate bigint NOT NULL,
  showProfileButton boolean NOT NULL DEFAULT TRUE,
  showSmallImage boolean NOT NULL DEFAULT TRUE
);

Create Table discordFriends(
  ID bigint NOT NULL,
  friendCode text NOT NULL,
  network tinyint NOT NULL,
  active boolean NOT NULL
);
