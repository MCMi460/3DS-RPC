#include <3ds.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>

static Handle frdHandle;

int main(int argc, char **argv)
{
	gfxInitDefault();
	frdInit();
	frdHandle = *frdGetSessionHandle();

	consoleInit(GFX_TOP, NULL);
	Result ret = 0, ret2 = 0, ret3 = 0;
	u64 friendCode = 0;
	u32 principalId = 0;
	FriendKey key;

	if (R_FAILED(ret = FRD_GetMyFriendKey(&key)))
		printf("FRD_GetMyFriendKey failed: %" PRId32 "\n", ret);
	else printf("LocalFriendCode: %llu\n", key.localFriendCode);

	/*if (R_FAILED(ret2 = FRD_PrincipalIdToFriendCode(HAHA FUCK YOU, &friendCode)))
		printf("FRD_PrincipalIdToFriendCode failed: %" PRId32 "\n", ret2);
	else printf("friendCode: %llu\n", friendCode);*/

	/*if (R_FAILED(ret3 = FRD_FriendCodeToPrincipalId(NOPE; NICE TRY THO, &principalId)))
		printf("FRD_FriendCodeToPrincipalId failed: %" PRId32 "\n", ret3);
	else printf("principalId: %lu\n", principalId);*/

	/*
		FUCK THIS
	*/

	frdExit();

	printf("Press START to exit.");


	while (aptMainLoop())
	{
		hidScanInput();
		if (hidKeysDown() & KEY_START) break;

		gfxFlushBuffers();
		gfxSwapBuffers();
		gspWaitForVBlank();
	}

	gfxExit();
	return 0;
}
