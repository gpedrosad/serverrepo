//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Item represents an existing item.
//////////////////////////////////////////////////////////////////////
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software Foundation,
// Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
//////////////////////////////////////////////////////////////////////

// include header file

#include "definitions.h"
#include "container.h"
#include "magic.h"
#include "player.h"
#include "tile.h"
#include "actions.h"

#include <iostream>
#include <sstream>
#include <iomanip>


Item* Item::CreateItem(const unsigned short _type, unsigned short _count /*= 0*/)
{
	Item *newItem;
	if(items[_type].isContainer()){
		newItem = new Container(_type);
	}
	else if(items[_type].isTeleport()){
		newItem = new Teleport(_type);
	}
	else if(items[_type].isMagicField()){
		newItem =  new Item(_type, _count);
	}
	else{
		newItem =  new Item(_type, _count);
	}
	newItem->isRemoved = false;
	newItem->useThing();
	return newItem;
}

//////////////////////////////////////////////////
// returns the ID of this item's ItemType
unsigned short Item::getID() const {
	return id;
}

//////////////////////////////////////////////////
// sets the ID of this item's ItemType
void Item::setID(unsigned short newid) {
	id = newid;
}

//////////////////////////////////////////////////
// return how many items are stacked or 0 if non stackable
unsigned short Item::getItemCountOrSubtype() const {
	if(isStackable()) {
		return count;
	}
	else if(isFluidContainer() || isSplash())
		return fluid;
	//else if(chargecount != 0)
	else if(items[id].runeMagLevel != -1)
		return chargecount;
	else
		return 0;
}

void Item::setItemCountOrSubtype(unsigned char n)
{
	if(isStackable()){
		/*if(n == 0){
			count = 1;
		}*/
		if(n > 100){
			count = 100;
		}
		else{
			count = n;
		}
	}
	else if(isFluidContainer() || isSplash())
		fluid = n;
	else if(items[id].runeMagLevel != -1)
		chargecount = n;
};

void Item::setActionId(unsigned short n){
	 if(n < 100)
	 	n = 100;
	actionId = n;
}

unsigned short Item::getActionId() const{
	return actionId;
}

void Item::setUniqueId(unsigned short n){
	//uniqueId only can be set 1 time
	if(uniqueId != 0)
		return;
	 if(n < 1000)
	 	n = 1000;
	uniqueId = n;
	ActionScript::AddThingToMapUnique(this);
}

unsigned short Item::getUniqueId() const{
	return uniqueId;
}

Item::Item(const unsigned short _type) {
	//std::cout << "Item constructor1 " << this << std::endl;
	id = _type;
	count = 0;
	chargecount = 0;
	fluid = 0;
	actionId = 0;
	uniqueId = 0;
	throwRange = 6;
	useCount = 0;
	isDecaying  = 0;
	specialDescription = NULL;
	text = NULL;

#ifdef YUR_RINGS_AMULETS
	const ItemType& it = items[id];
	time = it.newTime;
	charges = it.newCharges;
#endif //YUR_RINGS_AMULETS
#ifdef YUR_READABLES
	readable = NULL;
#endif //YUR_READABLES
#ifdef YUR_CLEAN_MAP
	decoration = false;
#endif //YUR_CLEAN_MAP
}

Item::Item(const Item &i){
	//std::cout << "Item copy constructor " << this << std::endl;
	id = i.id;
	count = i.count;
	chargecount = i.chargecount;
	throwRange = i.throwRange;
	useCount = 0;
	isDecaying  = 0;
	actionId = i.actionId;
	uniqueId = i.uniqueId;
	if(i.specialDescription != NULL){
		specialDescription = new std::string(*(i.specialDescription));
	}
	else{
		specialDescription = NULL;
	}
	if(i.text != NULL){
		text = new std::string(*(i.text));
	}
	else{
		text = NULL;
	}

#ifdef YUR_RINGS_AMULETS
	time = i.time;
	charges = i.charges;
#endif //YUR_RINGS_AMULETS
#ifdef YUR_READABLES
	if (i.readable)
		readable = new std::string(*(i.readable));
	else
		readable = NULL;
#endif //YUR_READABLES
#ifdef YUR_CLEAN_MAP
	decoration = i.decoration;
#endif //YUR_CLEAN_MAP
}

Item* Item::decay()
{
	unsigned short decayTo   = Item::items[getID()].decayTo;

	if(decayTo == 0) {
		return NULL;
	}

	if(dynamic_cast<Container*>(this)){
		if(items[decayTo].isContainer()){
			//container -> container
			setID(decayTo);
			return this;
		}
		else{
			//container -> no container
			Item *item = Item::CreateItem(decayTo,getItemCountOrSubtype());
			item->pos = this->pos;
			return item;
		}
	}
	else{
		if(items[decayTo].isContainer()){
			//no container -> container
			Item *item = Item::CreateItem(decayTo,getItemCountOrSubtype());
			item->pos = this->pos;
			return item;
		}
		else{
			//no contaier -> no container
			setID(decayTo);
			return this;
		}
	}
}

long Item::getDecayTime(){
	return items[id].decayTime*1000;
}

bool Item::rotate()
{
	if(items[id].rotable && items[id].rotateTo){
		id = items[id].rotateTo;
		return true;
	}
	return false;
}

Item::Item(const unsigned short _type, unsigned short _count) {
	//std::cout << "Item constructor2 " << this << std::endl;
	id = _type;
	count = 0;
	chargecount = 0;
	fluid = 0;
	actionId = 0;
	uniqueId = 0;
	useCount = 0;
	isDecaying  = 0;
	specialDescription = NULL;
	text = NULL;
	setItemCountOrSubtype((unsigned char)_count);
	/*
	if(isStackable()){
		if(_count == 0){
			count = 1;
		}
		else if(_count > 100){
			count = 100;
		}
		else{
			count = _count;
		}
	}
	else if(isFluidContainer() || isMultiType() )
		fluid = _count;
	else
		chargecount = _count;
	*/
	throwRange = 6;

#ifdef YUR_RINGS_AMULETS
	const ItemType& it = items[id];
	time = it.newTime;
	charges = it.newCharges;
#endif //YUR_RINGS_AMULETS
#ifdef YUR_READABLES
	readable = NULL;
#endif //YUR_READABLES
#ifdef YUR_CLEAN_MAP
	decoration = false;
#endif //YUR_CLEAN_MAP
}

Item::Item()
{
	//std::cout << "Item constructor3 " << this << std::endl;
	id = 0;
	count = 0;
	chargecount = 0;
	throwRange = 6;
	useCount = 0;
	isDecaying  = 0;
	actionId = 0;
	uniqueId = 0;
	specialDescription = NULL;
	text = NULL;

#ifdef YUR_RINGS_AMULETS
	time = 0;
	charges = 0;
#endif //YUR_RINGS_AMULETS
#ifdef YUR_READABLES
	readable = NULL;
#endif //YUR_READABLES
#ifdef YUR_CLEAN_MAP
	decoration = false;
#endif //YUR_CLEAN_MAP
}

Item::~Item()
{
	//std::cout << "Item destructor " << this << std::endl;
	if(specialDescription)
		delete specialDescription;
	if(text)
		delete text;

#ifdef YUR_READABLES
	if (readable)
		delete readable;
#endif //YUR_READABLES
}

bool Item::canMovedTo(const Tile *tile) const
{
	if(tile) {
		int objectstate = 0;

		if(isPickupable() || !isNotMoveable()) {
			objectstate |= BLOCK_PICKUPABLE;
		}

		if(isBlocking()) {
			objectstate |= BLOCK_SOLID;
		}

		return (tile->isBlocking(objectstate) == RET_NOERROR);
	}

	return false;
}

int Item::unserialize(xmlNodePtr p){
	char *tmp;
	tmp = (char*)xmlGetProp(p, (const xmlChar *) "id");
	if(tmp){
		id = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "special_description");
	if(tmp){
		specialDescription = new std::string(tmp);
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "text");
	if(tmp){
		text = new std::string(tmp);
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "count");
	if(tmp){
		setItemCountOrSubtype(atoi(tmp));
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "actionId");
	if(tmp){
		setActionId(atoi(tmp));
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "uniqueId");
	if(tmp){
		setUniqueId(atoi(tmp));
		xmlFreeOTSERV(tmp);
	}

#ifdef YUR_RINGS_AMULETS
	tmp = (char*)xmlGetProp(p, (const xmlChar *) "charges");
	if(tmp){
		charges = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}

	tmp = (char*)xmlGetProp(p, (const xmlChar *) "time");
	if(tmp){
		time = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}
#endif //YUR_RINGS_AMULETS

	return 0;
}

xmlNodePtr Item::serialize(){
	std::stringstream s;
	xmlNodePtr ret;
	ret = xmlNewNode(NULL,(const xmlChar*)"item");
	s.str(""); //empty the stringstream
	s << getID();
	xmlSetProp(ret, (const xmlChar*)"id", (const xmlChar*)s.str().c_str());

	if(specialDescription){
		s.str(""); //empty the stringstream
		s << *specialDescription;
		xmlSetProp(ret, (const xmlChar*)"special_description", (const xmlChar*)s.str().c_str());
	}

	if(text){
		s.str(""); //empty the stringstream
		s << *text;
		xmlSetProp(ret, (const xmlChar*)"text", (const xmlChar*)s.str().c_str());
	}

	s.str(""); //empty the stringstream
	if(getItemCountOrSubtype() != 0){
		s << getItemCountOrSubtype();
		xmlSetProp(ret, (const xmlChar*)"count", (const xmlChar*)s.str().c_str());
	}

	s.str("");
	if(actionId != 0){
		s << actionId;
		xmlSetProp(ret, (const xmlChar*)"actionId", (const xmlChar*)s.str().c_str());
	}

	s.str("");
	if(uniqueId != 0){
		s << uniqueId;
		xmlSetProp(ret, (const xmlChar*)"uniqueId", (const xmlChar*)s.str().c_str());
	}

#ifdef YUR_RINGS_AMULETS
	s.str("");
	if(charges != 0){
		s << charges;
		xmlSetProp(ret, (const xmlChar*)"charges", (const xmlChar*)s.str().c_str());
	}

	s.str("");
	if (time != 0){
		s << time;
		xmlSetProp(ret, (const xmlChar*)"time", (const xmlChar*)s.str().c_str());
	}
#endif //YUR_RINGS_AMULETS

	return ret;
}

bool Item::isBlocking() const {
	const ItemType& it = items[id];
	return it.blockSolid;
}

bool Item::isStackable() const {
	return items[id].stackable;
}

/*
bool Item::isMultiType() const {
	//return items[id].multitype;
	return (items[id].group == ITEM_GROUP_SPLASH);
}
*/

bool Item::isFluidContainer() const {
	return (items[id].isFluidContainer());
}

bool Item::isAlwaysOnTop() const {
	return items[id].alwaysOnTop;
}

bool Item::isNotMoveable() const {
	return !items[id].moveable;
}

bool Item::isGroundTile() const {
	return items[id].isGroundTile();
}

bool Item::isSplash() const{
	return items[id].isSplash();
}

bool Item::isPickupable() const {
	return items[id].pickupable;
}

bool Item::isUseable() const{
	return items[id].useable;
}

bool Item::floorChangeDown() const {
	return items[id].floorChangeDown;
}

bool Item::floorChangeNorth() const {
	return items[id].floorChangeNorth;
}
bool Item::floorChangeSouth() const {
	return items[id].floorChangeSouth;
}
bool Item::floorChangeEast() const {
	return items[id].floorChangeEast;
}
bool Item::floorChangeWest() const {
	return items[id].floorChangeWest;
}

bool Item::isWeapon() const
{
  //now also returns true on SHIELDS!!! Check back with getWeponType!
  //old: return (items[id].weaponType != NONE && items[id].weaponType != SHIELD && items[id].weaponType != AMO);
  return (items[id].weaponType != NONE && items[id].weaponType != AMO);
}

WeaponType Item::getWeaponType() const {
	  return items[id].weaponType;
}

amu_t Item::getAmuType() const{
	 return items[id].amuType;
}

subfight_t Item::getSubfightType() const {
	return items[id].shootType;
}

int Item::getAttack() const {
	  return items[id].attack;
}

int Item::getArmor() const {
	  return items[id].armor;
}

int Item::getDefense() const {
	  return items[id].defence;
}

int Item::getSlotPosition() const {
	return items[id].slot_position;
}

double Item::getWeight() const {
	if(isStackable()){
		return items[id].weight * std::max(1, (int)count);
	}

	if(items[id].runeMagLevel != -1) {
		unsigned char charges = getItemCharge();
		return items[id].weight * std::max(1, (int)(charges > 0 ? charges : 1));
	}

	return items[id].weight;
}

std::string Item::getFluidTypeName(unsigned char fluidType)
{
	switch(fluidType) {
		case FLUID_WATER: return "water";
		case FLUID_BLOOD: return "blood";
		case FLUID_BEER: return "beer";
		case FLUID_SLIME: return "slime";
		case FLUID_LEMONADE: return "lemonade";
		case FLUID_MILK: return "milk";
		case FLUID_MANAFLUID: return "manafluid";
		case FLUID_LIFEFLUID: return "lifefluid";
		case FLUID_OIL: return "oil";
		case FLUID_WINE: return "wine";
		case FLUID_STRONG_MANA: return "strong mana potion";
		default:
		{
			const std::string& name = items[fluidType].name;
			if(name.length())
				return name;
			return "unknown liquid";
		}
	}
}

#ifdef YUR_BOH
static int emeraldStacksFromAid(unsigned short aid, const Item& item)
{
	if(aid >= ITEM_EMERALD_SKILL_AID && aid <= ITEM_EMERALD_SKILL_AID_MAX)
		return aid - ITEM_EMERALD_SKILL_AID + 1;
	if(aid == ITEM_EMERALD_SKILL_AID_LEGACY && item.getArmor() > 0 && !item.isWeapon())
		return 3;
	return 0;
}

static bool isEmeraldImbueAid(unsigned short aid, const Item& item)
{
	return emeraldStacksFromAid(aid, item) > 0;
}

static int rubyStacksFromAid(unsigned short aid, const Item* item = NULL)
{
	if(item && isEmeraldImbueAid(aid, *item))
	 return 0;
	if(aid >= ITEM_RUBY_ATTACK_AID && aid <= ITEM_RUBY_ATTACK_AID_MAX)
		return aid - ITEM_RUBY_ATTACK_AID + 1;
	return 0;
}

static int nightglassStacksFromAid(unsigned short aid)
{
	if(aid >= ITEM_NIGHTGLASS_SPEED_AID && aid <= ITEM_NIGHTGLASS_SPEED_AID_MAX)
		return aid - ITEM_NIGHTGLASS_SPEED_AID + 1;
	return 0;
}

static int nightglassSpeedPercentFromStacks(int stacks)
{
	if(stacks <= 0)
		return 0;
	return stacks * 5;
}

static int nightglassAttackDelayFromStacks(int stacks)
{
	const int percent = nightglassSpeedPercentFromStacks(stacks);
	if(percent <= 0)
		return PLAYER_ATTACK_DELAY_MS;
	return PLAYER_ATTACK_DELAY_MS * (100 - percent) / 100;
}

static int crystalArrowStacksFromAid(unsigned short aid)
{
	if(aid >= ITEM_CRYSTAL_ARROW_SPEED_AID && aid <= ITEM_CRYSTAL_ARROW_SPEED_AID_MAX)
		return aid - ITEM_CRYSTAL_ARROW_SPEED_AID + 1;
	return 0;
}

static int crystalArrowSpeedPercentFromStacks(int stacks)
{
	if(stacks <= 0)
		return 0;
	return stacks * 5;
}

static int crystalArrowAttackDelayFromStacks(int stacks)
{
	const int percent = crystalArrowSpeedPercentFromStacks(stacks);
	if(percent <= 0)
		return PLAYER_ATTACK_DELAY_MS;
	return PLAYER_ATTACK_DELAY_MS * (100 - percent) / 100;
}

static int rubySpeedPercentFromStacks(int stacks)
{
	switch(stacks){
	case 1: return 5;
	case 2: return 9;
	case 3: return 16;
	default: return 0;
	}
}

static int rubyAttackDelayFromStacks(int stacks)
{
	const int percent = rubySpeedPercentFromStacks(stacks);
	if(percent <= 0)
		return PLAYER_ATTACK_DELAY_MS;
	return PLAYER_ATTACK_DELAY_MS * (100 - percent) / 100;
}

static void appendGemUseDescription(std::stringstream& s, unsigned short itemId)
{
	switch(itemId){
	case ITEM_YELLOW_GEM:
		s << std::endl << "Imbue: use on equipped boots (+10 haste/stack, max 3). Stacks with BOH.";
		break;
	case ITEM_VIOLET_GEM:
		s << std::endl << "Imbue: use on equipped wand or rod (+1 ML/stack, max 4).";
		break;
	case ITEM_BIG_RUBY:
		s << std::endl << "Imbue: use on equipped weapon (max 3: +5%, +9%, +16% attack speed; not wands). Nightglass dagger: up to 5 speed stacks.";
		break;
	case ITEM_BIG_EMERALD:
		s << std::endl << "Imbue: use on equipped armor (+3 sword/club/axe/dist, Paladin/Knight).";
		break;
	case ITEM_SMALL_AMETHYST:
		s << std::endl << "Tonka: trade 20 for a violet gem (imbue wand/rod).";
		break;
	case ITEM_SMALL_SAPPHIRE:
		s << std::endl << "Tonka: trade 20 for a yellow gem (imbue boots).";
		break;
	case ITEM_SMALL_RUBY:
		s << std::endl << "Tonka: trade 20 for a big ruby (imbue weapon).";
		break;
	case ITEM_SMALL_EMERALD:
		s << std::endl << "Tonka: trade 20 for a big emerald (imbue armor).";
		break;
	case ITEM_SMALL_DIAMOND:
		s << std::endl << "Tonka: trade 20 for a blue gem (imbue crystal arrow).";
		break;
	case ITEM_BLUE_GEM:
		s << std::endl << "Imbue: use on equipped crystal arrow (+5% attack speed/stack, max 5).";
		break;
	case ITEM_TALON:
	case ITEM_GOLD_NUGGET:
	case ITEM_SCARAB_COIN:
		s << std::endl << "Sell to Parived (say gems).";
		break;
	default:
		break;
	}
}
#endif //YUR_BOH

std::string Item::getDescription(bool fullDescription) const
{
	std::stringstream s;
	std::string str;
	const Container* container;
	const ItemType& it = items[id];

	if(specialDescription){
		s << (*specialDescription) << ".";

		if(fullDescription) {
			if(it.weight > 0)
				s << std::endl << "It weighs " << std::fixed << std::setprecision(1) << it.weight << " oz.";
		}
	}
	else if (it.name.length()) {
		if(id == ITEM_TRAIN_WAND) {
			s << "a train wand.";
			if(fullDescription) {
				double weight = getWeight();
				if(weight > 0)
					s << std::endl << "It weighs " << std::fixed << std::setprecision(1) << weight << " oz.";
			}
		}
		else if(isStackable() && count > 1) {
			s << (int)count << " " << it.name << "s.";

			if(fullDescription) {
				s << std::endl << "They weight " << std::fixed << std::setprecision(1) << ((double) count * it.weight) << " oz.";
			}
		}
		else {
			if(items[id].runeMagLevel != -1)
			{
				s << "a spell rune for level " << it.runeMagLevel << "." << std::endl;

				s << "It's an \"" << it.name << "\" spell (";
				if(getItemCharge())
					s << (int)getItemCharge();
				else
					s << "1";
				s << "x)";
			}
			else if(isWeapon() && (getAttack() || getDefense()))
			{
				s << article(it.name) << " (Atk:" << (int)getAttack() << " Def:" << (int)getDefense();
#ifdef YUR_BOH
				if(rubyStacksFromAid(actionId, this) > 0)
					s << ", +" << rubySpeedPercentFromStacks(rubyStacksFromAid(actionId, this)) << "% speed";
				else if(crystalArrowStacksFromAid(actionId) > 0)
					s << ", +" << crystalArrowSpeedPercentFromStacks(crystalArrowStacksFromAid(actionId)) << "% speed";
#endif //YUR_BOH
				s << ")";
			}
			else if(getArmor())
			{
				s << article(it.name) << " (Arm:"<< (int)getArmor() << ")";
			}
			else if(isFluidContainer()){
				s << article(it.name);
				if(fluid == 0){
					s << ". It is empty";
				}
				else{
					s << " of " << getFluidTypeName(fluid);
				}
				if(fullDescription && fluid == FLUID_STRONG_MANA) {
					s << std::endl << "It restores 250 mana. Sorcerers and druids level 50+ only.";
				}
			}
			else if(isSplash()){
				s << article(it.name) << " of ";
				if(fluid == 0){
					s << getFluidTypeName(FLUID_WATER);
				}
				else{
					s << getFluidTypeName(fluid);
				}
			}
			else if(it.isKey()){
				s << article(it.name) << " (Key:" << actionId << ")";
			}
			else if(it.isGroundTile()) //groundtile
			{
				s << it.name;
			}
#ifdef YUR_RINGS_AMULETS
			else if (charges)
			{
				s << article(it.name) << ". ";
				if (charges == 1)
					s << "\nIt has 1 charge left";
				else
					s << "\nIt has " << charges << " charges left";
			}
			else if (time)
			{
				s << article(it.name) << ". ";
				if (time < 60*1000)
					s << "\nIt has less than a minute left";
				else if (time == items[id].newTime)
					s << "\nIt is brand new";
				else
					s << "\nIt has " << (int)ceil(time/(60.0*1000.0)) << " minutes left";
			}
#endif //YUR_RINGS_AMULETS

			else if(it.isContainer() && (container = dynamic_cast<const Container*>(this))) {
				s << article(it.name) << " (Vol:" << container->capacity() << ")";
			}
			else {
				s << article(it.name);

#ifdef YUR_READABLES
				if (readable)
				{
					if (readable->empty())
						s << "\nNothing is written on it";
					else
						s << "\nYou read: " << *readable;
				}
#endif //YUR_READABLES
			}
			s << ".";
			if(fullDescription) {
				double weight = getWeight();
				if(weight > 0)
					s << std::endl << "It weighs " << std::fixed << std::setprecision(1) << weight << " oz.";

				if(items[id].description.length())
				{
					s << std::endl << items[id].description;
				}
			}
		}
	}
	else
		s<<"an item of type " << id <<".";

#ifdef YUR_BOH
	if(fullDescription){
		appendGemUseDescription(s, id);
	}
	if(actionId >= ITEM_HASTE_ENCHANT_AID && actionId <= ITEM_HASTE_ENCHANT_AID_MAX)
		s << std::endl << "Imbued: +" << (HASTE_ENCHANT_SPEED * (actionId - ITEM_HASTE_ENCHANT_AID + 1)) << " haste (" << (actionId - ITEM_HASTE_ENCHANT_AID + 1) << "/3).";
	else if(actionId >= ITEM_VIOLET_ML_AID && actionId <= ITEM_VIOLET_ML_AID_MAX)
		s << std::endl << "Imbued: +" << (actionId - ITEM_VIOLET_ML_AID + 1) << " ML (" << (actionId - ITEM_VIOLET_ML_AID + 1) << "/4).";
	else if(isEmeraldImbueAid(actionId, *this)) {
		const int stacks = emeraldStacksFromAid(actionId, *this);
		s << std::endl << "Imbued: +" << stacks << " sword/club/axe/dist (Paladin/Knight) (" << stacks << "/4).";
	}
	else if(rubyStacksFromAid(actionId, this) > 0 && fullDescription && isWeapon())
		s << std::endl << "It attacks faster: +" << rubySpeedPercentFromStacks(rubyStacksFromAid(actionId, this)) << "% speed ("
		  << rubyAttackDelayFromStacks(rubyStacksFromAid(actionId, this)) << "ms per hit, default " << PLAYER_ATTACK_DELAY_MS << "ms, "
		  << rubyStacksFromAid(actionId, this) << "/3).";
	else if(id == ITEM_MAGIC_TURBAN && fullDescription)
		s << std::endl << "Magic turban. Wearing it grants +1 magic level.";
	else if(id == ITEM_CRIMSON_HELMET && fullDescription)
		s << std::endl << "Knights, elite knights, paladins and royal paladins: +1 sword, club, axe and distance.";
	else if(id == ITEM_CRIMSON_WAND && fullDescription)
		s << std::endl << "Sorcerers, master sorcerers, druids and elder druids (level 33+): heavy magic missiles, 55-65 dmg, 13 mana, range 5. Imbue up to +4 ML.";
	else if(id == ITEM_TRAIN_WAND && fullDescription)
		s << std::endl << "Sorcerers, master sorcerers, druids and elder druids: trains magic level slowly on training dummies without spending mana.";
	else if(id == ITEM_FURY_CAPE && fullDescription)
		s << std::endl << "Sorcerers and druids: +1 magic level while worn.";
	else if(id == ITEM_MEDUSA_SWORD && fullDescription)
		s << std::endl << "Paralyzes players on every hit in PvP.";
	else if(id == ITEM_SWORD_OF_SILENCE && fullDescription)
		s << std::endl << "10% chance to silence a player for 2-3s in PvP (spoken spells only; 12s cooldown per target).";
	else if(id == ITEM_WINDSTING_AXE && fullDescription)
		s << std::endl << "20% chance to make a player drunk for 6s in PvP.";
	else if(id == ITEM_PRIVATE_TRAINER_DUMMY && fullDescription)
		s << std::endl << "Looks like a kit. Put it on a free house tile and use it (owner only, max 1 per house).";
	else if(id == ITEM_NIGHTGLASS_DAGGER && fullDescription) {
		s << std::endl << "A shadowy dagger. Imbue with a big ruby for up to 5 speed stacks (-10% success chance per stack).";
		const int ngStacks = nightglassStacksFromAid(actionId);
		if(ngStacks > 0)
			s << std::endl << "Imbued: +" << nightglassSpeedPercentFromStacks(ngStacks) << "% attack speed ("
			  << nightglassAttackDelayFromStacks(ngStacks) << "ms per hit, " << ngStacks << "/5).";
	}
	else if(id == ITEM_CRYSTAL_ARROW && fullDescription) {
		s << std::endl << "A throwable crystal missile (spear-like, " << CRYSTAL_ARROW_HIT_CHANCE
		  << "% hit). Imbue with a blue gem for up to 5 attack speed stacks.";
		const int caStacks = crystalArrowStacksFromAid(actionId);
		if(caStacks > 0)
			s << std::endl << "Imbued: +" << crystalArrowSpeedPercentFromStacks(caStacks) << "% attack speed ("
			  << crystalArrowAttackDelayFromStacks(caStacks) << "ms per hit, " << caStacks << "/5).";
	}
	else if(id == ITEM_SPEAR && fullDescription) {
		s << std::endl << "A throwable spear (" << SPEAR_HIT_CHANCE << "% hit chance).";
	}
#endif //YUR_BOH

#ifdef TLM_BUY_SELL
	if(fullDescription && id == ITEM_GOLDEN_AMULET)
		s << std::endl << "Equipado: el oro de monstruos que mates se deposita en tu banco al instante (sin abrir el cuerpo).";
	if(fullDescription && id == ITEM_GOLDEN_RING)
		s << std::endl << "Equipado en el slot de ring: ganas 20% mas oro de monstruos que mates.";
#endif //TLM_BUY_SELL

	str = s.str();
	return str;
}

std::string Item::getName() const
{
	return items[id].name;
}

void Item::setSpecialDescription(std::string desc){
	if(specialDescription){
		delete specialDescription;
		specialDescription = NULL;
	}
	if(desc.length() > 1)
		specialDescription = new std::string(desc);
}

std::string Item::getSpecialDescription()
{
	if(!specialDescription)
		return std::string("");
	return *specialDescription;
}

void Item::clearSpecialDescription(){
	if(specialDescription)
		delete specialDescription;
	specialDescription = NULL;
}

void Item::setText(std::string desc){
	if(text){
		delete text;
		text = NULL;
	}
	if(desc.length() > 1){
		text = new std::string(desc);
		if(items[id].readOnlyId != 0){//write 1 time
			id = items[id].readOnlyId;
		}
	}
}

void Item::clearText(){
	if(text)
		delete text;
	text = NULL;
}

std::string Item::getText()
{
	if(!text)
		return std::string("");
	return *text;
}

int Item::getRWInfo() const {
	return items[id].RWInfo;
}

bool Item::canDecay(){
	if(isRemoved)
		return false;
	return items[id].canDecay;
}
//Teleport class
Teleport::Teleport(const unsigned short _type) : Item(_type)
{
	useCount = 0;
	destPos.x = 0;
	destPos.y = 0;
	destPos.z = 0;
}

Teleport::~Teleport()
{
}

int Teleport::unserialize(xmlNodePtr p)
{
	Item::unserialize(p);
	char *tmp = (char*)xmlGetProp(p, (const xmlChar *) "destx");
	if(tmp){
		destPos.x = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}
	tmp = (char*)xmlGetProp(p, (const xmlChar *) "desty");
	if(tmp){
		destPos.y = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}
	tmp = (char*)xmlGetProp(p, (const xmlChar *) "destz");
	if(tmp){
		destPos.z = atoi(tmp);
		xmlFreeOTSERV(tmp);
	}


	return 0;
}

xmlNodePtr Teleport::serialize()
{
	xmlNodePtr xmlptr = Item::serialize();

	std::stringstream s;

	s.str(""); //empty the stringstream
	s << (int) destPos.x;
	xmlSetProp(xmlptr, (const xmlChar*)"destx", (const xmlChar*)s.str().c_str());

	s.str(""); //empty the stringstream
	s << (int) destPos.y;
	xmlSetProp(xmlptr, (const xmlChar*)"desty", (const xmlChar*)s.str().c_str());

	s.str(""); //empty the stringstream
	s << (int)destPos.z;
	xmlSetProp(xmlptr, (const xmlChar*)"destz", (const xmlChar*)s.str().c_str());

	return xmlptr;
}

int Item::getWorth() const
{
	switch(getID()){
	case ITEM_COINS_GOLD:
		return getItemCountOrSubtype();
	case ITEM_COINS_PLATINUM:
		return getItemCountOrSubtype() * 100;
	case ITEM_COINS_CRYSTAL:
		return getItemCountOrSubtype() * 10000;
	default:
		return 0;
	}
}

#ifdef YUR_RINGS_AMULETS
void Item::setGlimmer()
{
	switch (getID())
	{
		case ITEM_TIME_RING: setID(ITEM_TIME_RING_IN_USE); break;
		case ITEM_SWORD_RING: setID(ITEM_SWORD_RING_IN_USE); break;
		case ITEM_AXE_RING: setID(ITEM_AXE_RING_IN_USE); break;
		case ITEM_CLUB_RING: setID(ITEM_CLUB_RING_IN_USE); break;
		case ITEM_POWER_RING: setID(ITEM_POWER_RING_IN_USE); break;
		case ITEM_ENERGY_RING: setID(ITEM_ENERGY_RING_IN_USE); break;
		case ITEM_STEALTH_RING: setID(ITEM_STEALTH_RING_IN_USE); break;
		case ITEM_LIFE_RING: setID(ITEM_LIFE_RING_IN_USE); break;
		case ITEM_RING_OF_HEALING: setID(ITEM_RING_OF_HEALING_IN_USE); break;
	}
}

void Item::removeGlimmer()
{
	switch (getID())
	{
		case ITEM_TIME_RING_IN_USE: setID(ITEM_TIME_RING); break;
		case ITEM_SWORD_RING_IN_USE: setID(ITEM_SWORD_RING); break;
		case ITEM_AXE_RING_IN_USE: setID(ITEM_AXE_RING); break;
		case ITEM_CLUB_RING_IN_USE: setID(ITEM_CLUB_RING); break;
		case ITEM_POWER_RING_IN_USE: setID(ITEM_POWER_RING); break;
		case ITEM_ENERGY_RING_IN_USE: setID(ITEM_ENERGY_RING); break;
		case ITEM_STEALTH_RING_IN_USE: setID(ITEM_STEALTH_RING); break;
		case ITEM_LIFE_RING_IN_USE: setID(ITEM_LIFE_RING); break;
		case ITEM_RING_OF_HEALING_IN_USE: setID(ITEM_RING_OF_HEALING); break;
	}
}
#endif //YUR_RINGS_AMULETS
