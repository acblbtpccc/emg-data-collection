﻿#include <thread>
#include <iostream>
#include "DCAM560/Vzense_api_560.h"

using namespace std;

int main() {
	cout << "---RGBManualExposureSet---\n";

	uint32_t deviceCount;
	PsDeviceInfo* pDeviceListInfo = NULL;
	PsDeviceHandle deviceHandle = 0;
	PsReturnStatus status = PsRetOthers;

	//SDK Initialize
	status = Ps2_Initialize();
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "PsInitialize failed status:" <<status << endl;
		system("pause");
		return -1;
	}

	//1.Search and notice the count of devices.
	//2.get infomation of the devices. 
	//3.open devices accroding to the info.
GET:
	status = Ps2_GetDeviceCount(&deviceCount);
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "PsGetDeviceCount failed! make sure the DCAM is connected" << endl;
		this_thread::sleep_for(chrono::seconds(1));
		goto GET;
	}
	cout << "Get device count: " << deviceCount << endl;
	if (0 == deviceCount)
	{
		this_thread::sleep_for(chrono::seconds(1));
		goto GET;
	}

	pDeviceListInfo = new PsDeviceInfo[deviceCount];
	status = Ps2_GetDeviceListInfo(pDeviceListInfo, deviceCount);
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "GetDeviceListInfo failed status:" << status << endl;
		return -1;
	}
	else
	{
		if (Connected != pDeviceListInfo[0].status)
		{
			cout << "connect statu" << pDeviceListInfo[0].status << endl;
			cout << "Call Ps2_OpenDevice with connect status :" << Connected << endl;
			return -1;
		}
	}

	cout 
	<< "uri:" << pDeviceListInfo[0].uri << endl
	<< "alias:" << pDeviceListInfo[0].alias << endl
	<< "ip:" << pDeviceListInfo[0].ip << endl
	<< "connectStatus:" << pDeviceListInfo[0].status << endl;
	
	status = Ps2_OpenDeviceByIP(pDeviceListInfo[0].ip, &deviceHandle);
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "OpenDevice failed status:" <<status << endl;
		return -1;
	}
	uint32_t sessionIndex = 0;
	// set manual exposure enable
	bool bmanualEnabled = true;

	status = Ps2_SetRGBManualExposureEnabled(deviceHandle, sessionIndex, bmanualEnabled);
	cout << "Ps2_SetRGBManualExposureEnabled: " << status << "  ,   " << bmanualEnabled << endl;
	 
	// set absolute exposure time, in [1, 4000]
	uint16_t expore = 100;
	status = Ps2_SetRGBAbsoluteExposure(deviceHandle, sessionIndex, expore);
	if (PsRetOK == status)
	{
		cout << "Ps2_SetRGBAbsoluteExposure success , value: " << expore << endl;
	}
	else
	{
		cout << "Ps2_SetRGBAbsoluteExposure failed, status: " << status << endl;
	}
	// get absolute exposure time
	expore = 0;
	status = Ps2_GetRGBAbsoluteExposure(deviceHandle, sessionIndex, &expore);
	if (PsRetOK == status)
	{
		cout << "Ps2_GetRGBAbsoluteExposure success , value: " << expore << endl;
	}
	else
	{
		cout << "Ps2_GetRGBAbsoluteExposure failed, status: " << status << endl;
	}
	//1.close device
	//2.SDK shutdown
	status = Ps2_CloseDevice(&deviceHandle);
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "Ps2_CloseDevice failed status:" <<status<< endl;
		return -1;
	}
	status = Ps2_Shutdown();
	if (status != PsReturnStatus::PsRetOK)
	{
		cout << "Ps2_Shutdown failed status:" <<status<< endl;
		return -1;
	}
	cout << "---end---";

	return 0;
}
