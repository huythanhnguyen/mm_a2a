#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API module cho các thao tác liên quan đến sản phẩm
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from .base import APIClientBase

logger = logging.getLogger(__name__)

class ProductAPI(APIClientBase):
    """
    API Client cho các thao tác liên quan đến sản phẩm.
    """

    async def search_products(self, query: str, page_size: int = 10, current_page: int = 1) -> Dict[str, Any]:
        """
        Tìm kiếm sản phẩm.
        
        Args:
            query: Từ khóa tìm kiếm.
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm.
        """
        graphql_query = """
        query ProductSearch($search: String!, $pageSize: Int!, $currentPage: Int!) {
          products(search: $search, pageSize: $pageSize, currentPage: $currentPage, sort: { relevance: DESC }) {
            items {
              id
              sku
              name
              url_key
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
            total_count
          }
        }
        """
        
        variables = {
            "search": query,
            "pageSize": page_size,
            "currentPage": current_page
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def get_product_by_sku(self, sku: str) -> Dict[str, Any]:
        """
        Lấy thông tin sản phẩm theo SKU.
        
        Args:
            sku: SKU của sản phẩm.
            
        Returns:
            Dict[str, Any]: Thông tin sản phẩm.
        """
        graphql_query = """
        query GetProductBySku($sku: String!) {
          products(filter: { sku: { eq: $sku } }, pageSize: 1, currentPage: 1) {
            items {
              id
              uid
              sku
              name
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              media_gallery_entries {
                uid
                label
                position
                disabled
                file
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
          }
        }
        """
        
        variables = {
            "sku": sku
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def get_product_by_art_no(self, art_no: str) -> Dict[str, Any]:
        """
        Lấy thông tin sản phẩm theo Article Number.
        
        Args:
            art_no: Article Number của sản phẩm.
            
        Returns:
            Dict[str, Any]: Thông tin sản phẩm.
        """
        graphql_query = """
        query GetProductByArtNo($artNo: String!) {
          products(filter: { mm_art_no: { eq: $artNo } }) {
            items {
              id
              sku
              name
              url_key
              url_suffix
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
            total_count
          }
        }
        """
        
        variables = {
            "artNo": art_no
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def suggest_products(
        self,
        base_query: str,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        page_size: int = 10,
        current_page: int = 1
    ) -> Dict[str, Any]:
        """
        Đề xuất sản phẩm dựa trên query gốc với các bộ lọc và sắp xếp.
        
        Args:
            base_query: Query tìm kiếm cơ bản.
            filters: Các bộ lọc (giá, danh mục, thương hiệu...).
            sort: Tiêu chí sắp xếp (giá, mới nhất, bán chạy...).
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả đề xuất sản phẩm.
        """
        graphql_query = """
        query SuggestProducts(
            $search: String!,
            $filters: ProductAttributeFilterInput,
            $sort: ProductAttributeSortInput,
            $pageSize: Int!,
            $currentPage: Int!
        ) {
            products(
                search: $search,
                filter: $filters,
                sort: $sort,
                pageSize: $pageSize,
                currentPage: $currentPage
            ) {
                items {
                    id
                    sku
                    name
                    url_key
                    price {
                        regularPrice {
                            amount {
                                currency
                                value
                            }
                        }
                    }
                    price_range {
                        maximum_price {
                            final_price {
                                currency
                                value
                            }
                            discount {
                                amount_off
                                percent_off
                            }
                        }
                    }
                    small_image {
                        url
                    }
                    unit_ecom
                    description {
                        html
                    }
                    categories {
                        id
                        name
                        url_key
                    }
                    brand
                    new_from_date
                    special_from_date
                }
                total_count
                page_info {
                    page_size
                    current_page
                    total_pages
                }
                aggregations {
                    attribute_code
                    count
                    label
                    options {
                        label
                        value
                        count
                    }
                }
            }
        }
        """
        
        variables = {
            "search": base_query,
            "pageSize": page_size,
            "currentPage": current_page
        }
        
        if filters:
            variables["filters"] = filters
        
        if sort:
            variables["sort"] = sort
        
        try:
            result = await self.execute_graphql(graphql_query, variables)
            
            if result.get("success", False):
                data = result.get("data", {})
                products = data.get("products", {})
                
                # Thêm các gợi ý điều chỉnh tìm kiếm
                search_suggestions = []
                aggregations = products.get("aggregations", [])
                
                for agg in aggregations:
                    if agg["count"] > 0:
                        search_suggestions.append({
                            "type": agg["attribute_code"],
                            "label": agg["label"],
                            "options": agg["options"]
                        })
                
                return {
                    "success": True,
                    "data": {
                        "products": products,
                        "suggestions": search_suggestions
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi đề xuất sản phẩm: {str(e)}")
            return {
                "success": False,
                "message": f"Error suggesting products: {str(e)}",
                "code": "SUGGESTION_ERROR"
            }
            
    async def search_multiple_products(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        combine_mode: str = "union",
        page_size: int = 10,
        current_page: int = 1
    ) -> Dict[str, Any]:
        """
        Tìm kiếm nhiều từ khóa sản phẩm cùng lúc với các tùy chọn nâng cao.
        
        Args:
            keywords: Danh sách các từ khóa tìm kiếm.
            filters: Các bộ lọc chung cho tất cả từ khóa.
            sort: Tiêu chí sắp xếp kết quả.
            combine_mode: Cách kết hợp kết quả ("union" hoặc "intersection").
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm gộp lại.
        """
        results = []
        total_count = 0
        seen_ids = set()
        
        try:
            # Tìm kiếm song song cho tất cả từ khóa
            search_tasks = []
            for keyword in keywords:
                task = asyncio.create_task(
                    self.suggest_products(
                        base_query=keyword,
                        filters=filters,
                        sort=sort,
                        page_size=page_size,
                        current_page=current_page
                    )
                )
                search_tasks.append(task)
            
            # Chờ tất cả tìm kiếm hoàn thành
            search_results = await asyncio.gather(*search_tasks)
            
            # Xử lý kết quả theo combine_mode
            if combine_mode == "intersection":
                # Chỉ giữ lại sản phẩm xuất hiện trong TẤT CẢ từ khóa
                product_sets = []
                for result in search_results:
                    if result.get("success", False):
                        products = result.get("data", {}).get("products", {})
                        items = products.get("items", [])
                        product_ids = {item["id"] for item in items}
                        product_sets.append(product_ids)
                
                if product_sets:
                    common_ids = set.intersection(*product_sets)
                    # Lấy thông tin sản phẩm từ ID chung
                    for result in search_results:
                        if result.get("success", False):
                            products = result.get("data", {}).get("products", {})
                            items = products.get("items", [])
                            for item in items:
                                if item["id"] in common_ids and item["id"] not in seen_ids:
                                    results.append(item)
                                    seen_ids.add(item["id"])
                                    total_count += 1
            else:  # union mode
                # Gộp tất cả sản phẩm, loại bỏ trùng lặp
                for result in search_results:
                    if result.get("success", False):
                        products = result.get("data", {}).get("products", {})
                        items = products.get("items", [])
                        for item in items:
                            if item["id"] not in seen_ids:
                                results.append(item)
                                seen_ids.add(item["id"])
                                total_count += 1
            
            # Sắp xếp kết quả cuối cùng nếu cần
            if sort:
                results.sort(
                    key=lambda x: (
                        x.get("price", {}).get("regularPrice", {}).get("amount", {}).get("value", 0)
                        if sort.get("price") == "ASC"
                        else -x.get("price", {}).get("regularPrice", {}).get("amount", {}).get("value", 0)
                        if sort.get("price") == "DESC"
                        else 0
                    )
                )
            
            # Phân trang kết quả
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            paged_results = results[start_idx:end_idx]
            
            return {
                "success": True,
                "data": {
                    "products": {
                        "items": paged_results,
                        "total_count": total_count,
                        "page_info": {
                            "page_size": page_size,
                            "current_page": current_page,
                            "total_pages": (total_count + page_size - 1) // page_size
                        }
                    }
                },
                "message": f"Tìm thấy {total_count} sản phẩm phù hợp"
            }
                
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm nhiều từ khóa: {str(e)}")
            return {
                "success": False,
                "message": f"Error searching multiple keywords: {str(e)}",
                "code": "SEARCH_ERROR"
            } 