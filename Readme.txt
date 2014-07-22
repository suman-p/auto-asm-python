Folder Structure
------------------

--> "input" folder contains all the input files 
	
	-> Network.csv

--> "payload" folder contains all payloads
	
	-> CreateServerPool.txt
	-> Discovery_Server_payload.txt
	-> ManageDevice.txt
	-> Network.txt

--> "templates" folder contains all templates
	
	-> Template_Server_ESX.xml


--> BaseClass.py 
	
	Every Testcase can inherit this class so that it can use all existing functions

--> config.ini
	
	Input file

--> Discovery.py

	Sample Testcase

--> globalVars.py
	
	Includes all global variables

--> Services.xml

	URI Information for all Services   
