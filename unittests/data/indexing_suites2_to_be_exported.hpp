// Copyright 2004 Roman Yakovenko.
// Distributed under the Boost Software License, Version 1.0. (See
// accompanying file LICENSE_1_0.txt or copy at
// http://www.boost.org/LICENSE_1_0.txt)

#ifndef __indexing_suites2_to_be_exported_hpp__
#define __indexing_suites2_to_be_exported_hpp__

#include <vector>

namespace indexing_suites2 {

struct item_t{    
    item_t() : value( -1 ){}
    
    bool operator==(item_t const& item) const { 
        return value == item.value; 
    }
    
    bool operator!=(item_t const& item) const { 
        return value != item.value; 
    }    
    
    int value;
};


typedef std::vector<item_t> items_t;

inline item_t get_value( const std::vector<item_t>& vec, unsigned int index ){
    return vec.at(index);
}

inline void set_value( std::vector<item_t>& vec, unsigned int index, item_t value ){
    vec.at(index);
    vec[index] = value;
}

typedef std::vector<float> fvector;
fvector empty_fvector(){ return fvector(); }

}

#endif//__indexing_suites2_to_be_exported_hpp__