Create Table friends(
  friendCode bigint NOT NULL UNIQUE,
  online boolean NOT NULL UNIQUE,
  titleID text NOT NULL UNIQUE,
  updID text NOT NULL UNIQUE
);
