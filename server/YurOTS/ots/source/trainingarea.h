//////////////////////////////////////////////////////////////////////
// OpenTibia - an opensource roleplaying game
//////////////////////////////////////////////////////////////////////
// Training area by Yurez
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
#ifdef YUR_TRAINING_AREA

#ifndef TRAININGAREA_H
#define TRAININGAREA_H
#include "position.h"
class Game;

class TrainingArea
{
private:
	static bool AddTrainingTile(Game* game, const Position& pos, const Position& exit);
public:
	static bool Load(Game* game);
};
#endif //TRAININGAREA_H

#endif //YUR_TRAINING_AREA
