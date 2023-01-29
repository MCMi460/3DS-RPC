Create Table friends(
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
  lastOnline bigint NOT NULL
);

Create Table config(
  BACKEND_UPTIME bigint NOT NULL
);
