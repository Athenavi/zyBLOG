-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2023-09-23 04:41:26
-- 服务器版本： 8.0.34
-- PHP 版本： 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 数据库： `zy_blog`
--

-- --------------------------------------------------------

--
-- 表的结构 `comments`
--

CREATE TABLE `comments` (
  `username` varchar(255) NOT NULL,
  `article_name` char(255) NOT NULL,
  `comment` tinytext NOT NULL,
  `add_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- 表的结构 `invitecode`
--

CREATE TABLE `invitecode` (
  `uuid` char(36) NOT NULL,
  `code` char(4) NOT NULL,
  `is_used` tinyint(1) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

--
-- 转存表中的数据 `invitecode`
--

INSERT INTO `invitecode` (`uuid`, `code`, `is_used`) VALUES
('1', '9988', 1),
('2', '8989', 0);

-- --------------------------------------------------------

--
-- 表的结构 `ipcount`
--

CREATE TABLE `ipcount` (
  `visitId` int NOT NULL,
  `short_url` varchar(255) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `New_Old` char(1) DEFAULT 'N'
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- --------------------------------------------------------

--
-- 表的结构 `opentimes`
--

CREATE TABLE `opentimes` (
  `id` int NOT NULL,
  `short_url` varchar(10) NOT NULL,
  `response_count` int NOT NULL DEFAULT '0',
  `first_response_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- --------------------------------------------------------

--
-- 表的结构 `urls`
--

CREATE TABLE `urls` (
  `id` int NOT NULL,
  `long_url` varchar(255) NOT NULL,
  `short_url` varchar(10) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `username` varchar(255) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- --------------------------------------------------------

--
-- 表的结构 `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `ifAdmin` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

--
-- 转存表中的数据 `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `ifAdmin`) VALUES
(1, 'test', '$2b$12$1FjwIi8RHii.F21p1D5c8OXuhM7Ksdyet77AQ4bI6kpFlmv41Bo0i', 1);

--
-- 转储表的索引
--

--
-- 表的索引 `invitecode`
--
ALTER TABLE `invitecode`
  ADD PRIMARY KEY (`uuid`);

--
-- 表的索引 `ipcount`
--
ALTER TABLE `ipcount`
  ADD PRIMARY KEY (`visitId`);

--
-- 表的索引 `opentimes`
--
ALTER TABLE `opentimes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `short_url_unique` (`short_url`);

--
-- 表的索引 `urls`
--
ALTER TABLE `urls`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `ipcount`
--
ALTER TABLE `ipcount`
  MODIFY `visitId` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=29;

--
-- 使用表AUTO_INCREMENT `opentimes`
--
ALTER TABLE `opentimes`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=26;

--
-- 使用表AUTO_INCREMENT `urls`
--
ALTER TABLE `urls`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
